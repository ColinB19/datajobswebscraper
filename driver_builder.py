"""
This script is adapted from this GitHub Repo: https://github.com/shawnbutton/PythonHeadlessChrome/tree/master. I needed
an effective way of downloading excel files in headless mode and not having to deal with the download popup in chrome. 
The download popup cannot be controlled by selenium, so I needed the files to be pushed to a specific directory automatically.
I tried many (many, many) solutions,  and this was the most effective!

I've modified the code to automatically download the latest chrome driver if not already installed, and to emulate a user 
browser using headers (which is oddly not the default selenium behavior). 

"""

from selenium.webdriver import Chrome
from selenium.webdriver.chrome import webdriver as chrome_webdriver


from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class DriverBuilder:
    """Class to build a chrome driver in selenium. The key functionality is it allows chrome to automatically download files to a
    specific directory without the usual download prompt window. It also grabs the latest Chrome driver automatically, enables some
    safebrowsing options, and emulates a user browser by using headers."""

    def get_driver(
        self, download_location: str = None, headless: bool = False
    ) -> chrome_webdriver:
        """Calls the driver configuration manager and sets the chrome window size

        Keyword Arguments:
        download_location -- path to where files will be automatically downloaded, defaults to system defualt.
        headless -- tells the scraper to open up a browswer window or just run the driver in the background.
        """
        driver = self._get_chrome_driver(download_location, headless)

        driver.set_window_size(1400, 700)

        return driver

    def _get_chrome_driver(
        self, download_location: str = None, headless: bool = False
    ) -> chrome_webdriver:

        # enables passing of chrome options to header
        chrome_options = chrome_webdriver.Options()
        if download_location:
            prefs = {
                "download.default_directory": download_location,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True,
            }

            chrome_options.add_experimental_option("prefs", prefs)

        if headless:
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # tells the browswer that I am human while in headless mode
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
            chrome_options.add_argument(f"user-agent={user_agent}")

        # enables automatic installation of chrome drivers
        service = Service(ChromeDriverManager().install())
        driver = Chrome(service=service, options=chrome_options)
        if headless:
            self.enable_download_in_headless_chrome(driver, download_location)

        return driver

    def enable_download_in_headless_chrome(self, driver, download_dir):
        """
        there is currently a "feature" in chrome where
        headless does not allow file download: https://bugs.chromium.org/p/chromium/issues/detail?id=696481
        This method is a hacky work-around until the official chromedriver support for this.
        Requires chrome version 62.0.3196.0 or above.
        """

        # add missing support for chrome "send_command"  to selenium webdriver
        driver.command_executor._commands["send_command"] = (
            "POST",
            "/session/$sessionId/chromium/send_command",
        )

        params = {
            "cmd": "Page.setDownloadBehavior",
            "params": {"behavior": "allow", "downloadPath": download_dir},
        }
        command_result = driver.execute("send_command", params)
        print("response from browser:")
        for key in command_result:
            print("result:" + key + ":" + str(command_result[key]))
