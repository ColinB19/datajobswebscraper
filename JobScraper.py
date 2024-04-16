from driver_builder import DriverBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
import numpy as np
import regex as re
from datetime import datetime
import time
import logging
from string import punctuation

from lists_and_dicts import state_codes, street_sfx, state_map

wait_time = 3
PATH = '/home/colin/Documents/Code/DS Projects/Wellfound Webscraper/DATA'
LOG_PATH = '/home/colin/Documents/Code/DS Projects/Wellfound Webscraper/LOGS'
HEADLESS = False
WAIT_TIME = 10

dj_site = 'https://datajobs.com/'
indeed_site = 'https://indeed.com/'
# this pattern pulls jobs specifically from datajobs
dj_pattern = r"<a href=\"(.*)\"><strong>(.*)</strong> – <span [^\>]*>(.*)</span></a>[\n\s]*</div>[\n\s]*<div[^\>]*>[\n\s]*<em>[\n\s]*<span[^\>]*>(.*)</span>[\n\s]*[\&nbsp;\•]*[\n\s]*\$*([\d,]*)[–\s]*\$*([\d,]*)[\n\s]*</em>"
col_list = [
    'url',
    'title',
    'company',
    'location',
    'salary_lower',
    'salary_upper'
]

logging.basicConfig(
    filename=LOG_PATH + "/main.log",
    format="%(levelname)s - %(asctime)s:%(message)s",
    encoding="utf-8",
    level=logging.INFO,
)

def cleanhtml(raw_html):
    """To clean up HTML. Removes all HTML tags and comments. Leaves plain text.

    Input:
    ------
        raw_html -> string: html scraped from a website
    Output:
    -------
        cleantext -> string: text from rawhtml with HTML comments and tags removed
    """
    raw_html2 = re.sub("(<!--.*?-->)", "", raw_html, flags=re.DOTALL)
    cleantext = re.sub(
        "<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});", " ", raw_html2
    )
    return cleantext


def remove_style_tags(html_string):
    # Regex pattern to match <style> tags and their content
    style_pattern = re.compile(
        r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", re.IGNORECASE
    )
    # Remove <style> tags and their content from the HTML string
    cleaned_html = style_pattern.sub("", html_string)
    return cleaned_html


def remove_script_tags(html_string):
    # Regex pattern to match <script> tags and their content
    script_pattern = re.compile(
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.IGNORECASE
    )
    # Remove <script> tags and their content from the HTML string
    cleaned_html = script_pattern.sub("", html_string)
    return cleaned_html


def clean_title(title):
    temp_title = title.lower().replace(" ", "")
    # let's just lump leadership/management positions into one category since we aren't really looking for these
    if (
        "headof" in temp_title
        or "chief" in temp_title
        or "president" in temp_title
        or "director" in temp_title
        or "manager" in temp_title
    ):
        return "Leadership"
    # software engineering is also not quite what we're looking for
    elif "software" in temp_title and (
        "engineer" in temp_title or "developer" in temp_title
    ):
        return "Software Engineer"
    # here we are mapping the standard data positions. Note that job titles can be Data Scientist - Ads or something like that, this helps us just grab the position title
    elif "data" in temp_title:
        if "scientist" in temp_title or "science" in temp_title:
            return "Data Scientist"
        # here we are generalizing a lot of different positions into one. It's ok for a general overview
        # NOTE: This logic will capture the 'Data Science Engineer' role, since Data Engineering tends to be more in demand, I'm ok with that.
        elif (
            "engineer" in temp_title
            or "warehouse" in temp_title
            or "architect" in temp_title
            or "base" in temp_title
        ):
            return "Data Engineer"
        elif "analyst" in temp_title:
            return "Data Analyst"
        else:
            return title
    # BI Engineer could probably be lumped into data analyst if necessary; although, in big companies they can be very different
    elif (
        ("business" in temp_title and "intelligence" in temp_title)
        or ("business" in temp_title and "analyst" in temp_title)
        or "bi " in title.lower()
    ):
        return "BI Engineer"
    # this is highly specific we could probably stand to workshop this a bit
    elif (
        "machine" in temp_title
        and "learning" in temp_title
        and ("engineer" in temp_title or "scientist" in temp_title)
    ):
        return "Machine Learning Engineer"
    # this captures all the analysts not caught in the 'data' step
    elif "analyst" in temp_title:
        return "Data Analyst"
    elif "statistician" in temp_title:
        return "Statistician"
    elif "hadoop" in temp_title:
        return "Data Engineer"
    else:
        return title


def get_state_code(addr):
    if addr != addr or addr is None:
        return None

    # a lot of these have the word "in" in them, let's remove it
    addr = addr.replace(" in ", " ")

    addr_1 = re.sub(f"[{punctuation}]", "", addr)
    sfx_idx = []

    for sfx in street_sfx:
        try:
            addr_1.lower().index(f" {sfx.lower()} ")
        except:
            continue
        else:
            sfx_idx.append({sfx: addr_1.lower().index(f" {sfx.lower()} ")})

    if len(sfx_idx) > 1:
        # for the most part, we can just take the max index here
        idx = -1
        for match in sfx_idx:
            temp_idx = list(match.values())[0]
            if temp_idx > idx:
                idx = temp_idx
                sfx_len = len(list(match.keys())[0])
        addr_1_sub = addr_1[idx + sfx_len + 1 :]
        addr_1_sub = addr_1
    elif len(sfx_idx) == 1:
        idx = list(sfx_idx[0].values())[0]
        sfx_len = len(list(sfx_idx[0].keys())[0])
        addr_1_sub = addr_1[idx + sfx_len + 1 :]
    else:
        addr_1_sub = addr_1

    states = []
    for st in state_codes:
        if st in addr_1_sub.split():
            states.append(st)

    # if we did not find anything, try looking through actual state names
    if not states:
        for st in state_codes:
            if state_map[st].lower() in addr_1_sub.lower():
                states.append(st)

    # finally, if we found a couple codes, check if 'NE' is one of them
    # that probably applies to the street
    # NOTE: no other cardinal directions are state codes
    if len(states) > 1 and "NE" in states:
        states.remove("NE")

    if len(states) > 1:
        print(f"too many states!!!: {addr} || {states}")
    elif len(states) == 1:
        return states[0]
    else:
        return None


class DataJobsScraper:

    def __init__(self, site):

        self._site = site
        self.job_meta = pd.DataFrame(
            columns=[
                "url",
                "title",
                "company",
                "location",
                "salary_lower",
                "salary_upper",
                "job_category",
                "site",
            ]
        )

    def scrape_jobs(self):
        driver_builder = DriverBuilder()
        self._driver = driver_builder.get_driver(
            download_location=PATH, headless=HEADLESS
        )

        if self._site == "DataJobs":
            self._site_url = "https://datajobs.com/"
            # there are two different boards on this website
            self.__scrape_datajobs()
        elif self._site == "Indeed":
            self._site_url = "https://indeed.com/"
            self.__scrape_indeed()
        # just dedup jobs before moving on
        self.job_meta.drop_duplicates(
            subset=self.job_meta.columns.tolist()[:-1], inplace=True
        )
        self.job_meta["job_id"] = self.job_meta.index + 1
        self.job_meta["pull_date"] = datetime.today().strftime(r"%m/%d/%Y")

    def scrape_job_text(self):

        if self._site == "DataJobs":
            job_desc_list = self.__scrape_datajob_desc()
        elif self._site == "Indeed":
            job_desc_list = self.__scrape_indeed_desc()

        self.job_descriptions = pd.DataFrame(job_desc_list)

    def clean_data(self):
        # let's clean up the data a bit
        # I noticed that New York City, NY is just represented as New York City. This doesn't work for pulling out the states later so let's just replace it
        self.job_meta.location = self.job_meta.location.replace(
            {"New York City": "New York City, NY"}
        )
        # This is an HTML code for ampersand. Let's just replace it with an actual ampersand
        self.job_meta["title"] = self.job_meta["title"].replace({"&amp;": "&"})
        # Let's get the states (note, there are non-US jobs in this dataset)
        # self.job_meta['state'] = self.job_meta.loc[:,'location'].fillna('').apply(lambda x: x.replace(' ', '').split(',')[1] if ',' in x else x)
        self.job_meta["state"] = (
            self.job_meta.loc[:, "location"]
            .fillna("")
            .apply(lambda x: get_state_code(x))
        )
        # finally, let's clean up the job titles a bit based on some hard coded rules. This is not fool proof but it gives us a much better idea of what jobs are on this site.
        self.job_meta["clean_title"] = self.job_meta["title"].apply(clean_title)

    def export_data(self, data_path):
        self._driver.close()
        try:
            # grab old data
            old_jm = pd.read_csv(f"{data_path}/{self._site}_job-meta.csv")
            old_jd = pd.read_csv(f"{data_path}/{self._site}_job-descriptions.csv")
        except:
            # TODO: Fix comma issue, maybe just by making things excel files
            self.job_meta.to_csv(f"{data_path}/{self._site}_job-meta.csv", index=False)
            self.job_descriptions.to_csv(
                f"{data_path}/{self._site}_job-descriptions.csv", index=False
            )
        else:
            # set the new indexes
            self.job_meta["job_id"] = self.job_meta["job_id"] + old_jm["job_id"].max()
            self.job_descriptions["job_id"] = (
                self.job_descriptions["job_id"] + old_jd["job_id"].max()
            )

            # drop duplicate jobs
            comb_jm = pd.concat(
                [old_jm, self.job_meta], ignore_index=True
            ).drop_duplicates(
                subset=["url", "title", "company", "location"],
                keep="first",
                ignore_index=True,
            )
            # drop duplicate descriptions. NOTE: This logic will prevent keeping jobs where the poster edited the job posting text
            comb_jd = pd.concat([old_jd, self.job_descriptions], ignore_index=True)
            comb_jd = comb_jd[comb_jd["job_id"].isin(list(comb_jm["job_id"].values))]

            # TODO: Fix comma issue, maybe just by making things excel files
            comb_jm.to_csv(f"{data_path}/{self._site}_job-meta.csv", index=False)
            comb_jd.to_csv(
                f"{data_path}/{self._site}_job-descriptions.csv", index=False
            )

    def __scrape_datajobs(self):
        board_paths = ["/Data-Science-Jobs", "/Data-Engineering-Jobs"]
        # loop through the boards available
        for bp in board_paths:
            if bp == "/Data-Science-Jobs":
                cat = "Data Science & Analytics"
            else:
                cat = "Data Engineering"
            # load into the webpage
            self._driver.get(self._site_url + bp)
            more_pages = True  # will kill the loop when there are no more pages
            i = 0  # just a counter to kill the loop just in case
            while more_pages:
                # grab page source html
                page_html = self._driver.page_source

                # grab job info
                fall = re.findall(dj_pattern, page_html)

                # create pandasable list
                fall_cols = [dict(zip(self.job_meta.columns, x + (cat,))) for x in fall]

                # add to dataframe
                self.job_meta = pd.concat(
                    [self.job_meta, pd.DataFrame(fall_cols)], ignore_index=True
                )

                if i == 200:
                    # stop after 200 pages
                    more_pages = False

                # try to go to next page
                try:
                    next_page = WebDriverWait(self._driver, wait_time).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//a[contains(text(), 'NEXT PAGE')]")
                        )
                    )
                    next_page.click()
                    i += 1
                except:
                    print("END OF SEARCH RESULTS...")
                    more_pages = False
        self.job_meta["site"] = self._site_url

    def __scrape_datajob_desc(self):
        job_desc_list = []
        for _, job in self.job_meta.iterrows():
            job_url = self._site_url + job["url"][1:]
            self._driver.get(job_url)
            # grab job desc element
            try:
                job_descr = WebDriverWait(self._driver, wait_time).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//div[@id='job_description']//*[@class='jobpost-table-cell-2']",
                        )
                    )
                )
            except:
                print(f"I can't find this job: {job['title']}")
                continue
            # get html
            job_desc_clean = cleanhtml(job_descr.get_attribute("innerHTML"))
            job_desc_list.append(
                {
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": job["company"],
                    "desc": job_desc_clean,
                }
            )
        return job_desc_list

    def __scrape_indeed(self):
        # states = ['California', 'Texas', 'Washington State', 'New York', 'Florida', 'Colorado', 'Oregon', 'Illinois', 'Massachusetts']
        states = ["United States"]
        jobs = ["Data Scientist", "Data Analyst", "Data Engineer"]

        # states = ['California']
        # jobs = ['Data Scientist']

        for state in states:
            for job in jobs:

                # we are having a frequest request issue, let's try some rate limiting
                time.sleep(np.random.randint(0, 1) / 10)

                bp = f"jobs?q={job.lower().replace(' ','+')}&l={state}"
                self._driver.get(self._site_url + bp)

                more_pages = True  # will kill the loop when there are no more pages
                i = 0  # just a counter to kill the loop just in case
                while more_pages:

                    # grab page source html
                    page_html = self._driver.page_source

                    # scrape job titles
                    titles = re.findall(
                        "<span[^>]*jobTitle[^>]*>(?<=>)(.*?)(?=<)", page_html
                    )

                    # scrape job links
                    links = re.findall(
                        '<h2[^>]*jobTitle[^>]*><a[^>]*href="([^">]*)">', page_html
                    )

                    clean_links = self.__clean_indeed_link(links=links)

                    # this is just in order to get it into the same format as the DataJobs scraper
                    nan_list = [np.nan for idx in range(len(titles))]
                    job_cats = [job for idx in range(len(titles))]
                    fall = list(
                        zip(
                            clean_links,
                            titles,
                            nan_list,
                            nan_list,
                            nan_list,
                            nan_list,
                            job_cats,
                        )
                    )

                    # create pandasable list
                    fall_cols = [dict(zip(self.job_meta.columns, x)) for x in fall]

                    # add to dataframe
                    self.job_meta = pd.concat(
                        [self.job_meta, pd.DataFrame(fall_cols)], ignore_index=True
                    )

                    if i == 200:
                        # stop after 200 pages
                        more_pages = False

                    # try to go to next page
                    try:
                        next_page = WebDriverWait(self._driver, wait_time).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(@data-testid, 'pagination-page-next')]",
                                )
                            )
                        )
                        next_page.click()
                        i += 1
                    except:
                        print("END OF SEARCH RESULTS...")
                        more_pages = False
            self.job_meta["site"] = self._site_url

    def __scrape_indeed_desc(self):
        job_desc_list = []
        for idx, job in self.job_meta.iterrows():
            # we are having a frequest request issue, let's try some rate limiting
            time.sleep(np.random.randint(1, 15) / 10)

            # for indeed jobs we store the full url here
            self._driver.get(job["url"])

            # get the source html
            page_html = self._driver.page_source
            page_html = remove_script_tags(page_html)
            page_html = remove_style_tags(page_html)
            # strip out the script and styling

            # grab company name
            company_name = re.findall(
                r"data-company-name[^>]*><span[^>]*><a[^>]*>([^<]*)<", page_html
            )

            if len(company_name) == 1:
                self.job_meta.loc[idx, "company"] = company_name[0]
            else:
                print(
                    f"Not the correct number of company names for ID:{job['job_id']} TITLE: {job['title']}. Found: {company_name}"
                )
                company_name = [""]

            # grab salary
            pay = re.findall(
                r"salaryInfoAndJobType[^>]*><span[^>]*>([^<]*)<", page_html
            )

            if len(pay) == 1:
                # makes sure there are numbers in the string and that it isn't empty
                if pay[0].strip() != "" and re.findall(r"\d", pay[0]):
                    pay_range = self.__pay_handler(pay[0])
                    try:
                        self.job_meta.loc[idx, "salary_lower"] = pay_range[0]
                        self.job_meta.loc[idx, "salary_upper"] = pay_range[1]
                    except:
                        self.job_meta.loc[idx, "salary_lower"] = pay_range[0]
            else:
                print(
                    f"Not the correct number of salaries for ID:{job['job_id']} TITLE: {job['title']} Found: {pay}"
                )

            # grab location
            location = re.findall(
                r"jobLocationText[^>]*><div[^>]*><span[^>]*>([^<]*)<", page_html
            )
            # NOTE: There are two different patterns I've found here
            if not location:
                location = re.findall(r"job-location[^>]*>([^<]*)</div", page_html)

            if len(location) == 1 or len(location) == 2:
                self.job_meta.loc[idx, "location"] = location[0]
            else:
                print(
                    f"Not the correct number of locations for ID:{job['job_id']} TITLE: {job['title']}. Found: {location}"
                )

            # grab job description
            try:
                job_descr = WebDriverWait(self._driver, wait_time).until(
                    EC.element_to_be_clickable((By.ID, "jobDescriptionText"))
                )
            except:
                print(f"I can't find this job: {job['title']}")
                continue

            # get html
            job_desc_clean = cleanhtml(job_descr.get_attribute("innerHTML"))
            job_desc_list.append(
                {
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": company_name[0],
                    "desc": job_desc_clean,
                }
            )
        return job_desc_list

    def __pay_handler(self, pay_string):

        # split on the dash
        pays = pay_string.split("-")
        # remove all non-numeric characters
        try:
            pays = [float(re.sub(r"[^\d\.]*", "", x)) for x in pays]
        except ValueError:
            print(f"couldn't convert to float: {pay_string}")
        if len(pays) > 2:
            print(f"there are too many pays! {pay_string}")
            return pay_string

        if "year" in pay_string:
            return pays
        elif "month" in pay_string:
            # we only want to return yearly salaries
            return [12 * x for x in pays]
        elif "week" in pay_string:
            return [52 * x for x in pays]
        elif "day" in pay_string:
            return [255 * x for x in pays]
        elif "hour" in pay_string or "hr" in pay_string:
            return [40 * 52 * x for x in pays]
        elif pays[0] > 30_000:
            return pays[0]
        else:
            print(f"Pay error. not sure how to parse: {pay_string}")
            return pay_string

    def __clean_indeed_link(self, links):
        clean_links = []
        for link in links:
            if link.startswith("/rc/clk?"):
                clean_links.append(
                    "https://www.indeed.com/viewjob?" + link[8:].replace("&amp;", "&")
                )
            elif link.startswith("/pagead"):
                clean_links.append(
                    "https://www.indeed.com" + link.replace("&amp;", "&")
                )
            else:
                print(f"We haven't handled this link type: {link[:20]}")
                clean_links.append(link)

        return clean_links

