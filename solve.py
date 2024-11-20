import argparse
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

@dataclass
class Config:
    """Configuration settings for the application."""
    url: str = ""
    password: str = ""
    download_dir: Path = Path.cwd() / 'config_files'
    timeout: int = 10  # Seconds to wait for elements
    download_wait: int = 15  # Seconds to wait for downloads

class WebAutomation:
    """Handles web automation tasks using Selenium."""
    
    def __init__(self, config: Config):
        self.config = config
        self.config.download_dir.mkdir(exist_ok=True)
        self.driver = self._setup_driver()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _setup_driver(self) -> webdriver.Chrome:
        """Configure and return Chrome WebDriver."""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        prefs = {
            "download.default_directory": str(self.config.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

    def _wait_for_element(self, by: By, value: str, timeout: Optional[int] = None) -> Optional[webdriver.remote.webelement.WebElement]:
        """Wait for element to be present and return it."""
        try:
            return WebDriverWait(self.driver, timeout or self.config.timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {value}")
            return None

    def _verify_download(self, filename: str) -> bool:
        """Verify if file has been downloaded successfully."""
        file_path = self.config.download_dir / filename
        start_time = time.time()
        
        while time.time() - start_time < self.config.download_wait:
            if file_path.exists():
                return True
            time.sleep(1)
        
        return False

    def login(self) -> bool:
        """Perform login if needed."""
        try:
            # Check if already logged in
            if self._wait_for_element(By.XPATH, "//p[contains(text(), 'Clients')]", timeout=2):
                self.logger.info("Already logged in")
                return True

            self.logger.info("Logging in...")
            self.driver.get(self.config.url)
            
            password_field = self._wait_for_element(By.XPATH, "/html/body/div/div/div/form/input[1]")
            login_button = self._wait_for_element(By.XPATH, "/html/body/div/div/div/form/input[2]")
            
            if not (password_field and login_button):
                return False
            
            password_field.clear()
            password_field.send_keys(self.config.password)
            login_button.click()
            
            # Verify login success
            return bool(self._wait_for_element(By.XPATH, "//p[contains(text(), 'Clients')]"))
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def add_name(self, name: str) -> bool:
        """Add a new name to the system."""
        try:
            if not self.login():
                return False

            # Click add button
            add_button = self._wait_for_element(
                By.XPATH, 
                "/html/body/div/div/div/div[3]/div[1]/div[2]/button"
            )
            if not add_button:
                return False
            add_button.click()

            # Enter name
            input_box = self._wait_for_element(
                By.XPATH,
                "/html/body/div/div/div/div[4]/div/div[2]/div[1]/div/div[2]/div/p/input"
            )
            if not input_box:
                return False
            input_box.clear()
            input_box.send_keys(name)

            # Submit
            submit_button = self._wait_for_element(
                By.XPATH,
                "/html/body/div/div/div/div[4]/div/div[2]/div[2]/button[1]"
            )
            if not submit_button:
                return False
            submit_button.click()

            # Verify addition
            verification = self._wait_for_element(
                By.XPATH,
                f"//span[text()='{name}']/ancestor::div[contains(@class, 'relative')]"
            )
            success = bool(verification)
            self.logger.info(f"{'Successfully added' if success else 'Failed to add'} {name}")
            return success

        except Exception as e:
            self.logger.error(f"Error adding {name}: {str(e)}")
            return False

    def download_configuration(self, name: str) -> bool:
        """Download configuration for a given name."""
        try:
            if not self.login():
                return False

            # Find person element
            person_element = self._wait_for_element(
                By.XPATH,
                f"//span[text()='{name}']/ancestor::div[contains(@class, 'relative')]"
            )
            if not person_element:
                self.logger.error(f"Could not find element for {name}")
                return False

            # Find and click download link
            download_link = person_element.find_element(By.XPATH, ".//a[@title='Download Configuration']")
            download_url = download_link.get_attribute('href')
            self.logger.info(f"Downloading configuration for {name}")
            
            self.driver.get(download_url)
            
            # Verify download
            if self._verify_download(f"{name}.conf"):
                self.logger.info(f"Successfully downloaded configuration for {name}")
                return True
            else:
                self.logger.error(f"Download verification failed for {name}")
                return False

        except Exception as e:
            self.logger.error(f"Error downloading configuration for {name}: {str(e)}")
            return False

    def process_name_list(self, names: List[str], operation: str):
        """Process a list of names with progress bar."""
        operation_map = {
            'add': self.add_name,
            'download': self.download_configuration
        }
        
        if operation not in operation_map:
            self.logger.error(f"Invalid operation: {operation}")
            return
        
        func = operation_map[operation]
        success_count = 0
        
        with tqdm(total=len(names), desc=operation.capitalize()) as pbar:
            for name in names:
                if func(name):
                    success_count += 1
                pbar.update(1)
        
        self.logger.info(f"{operation.capitalize()} completed: {success_count}/{len(names)} successful")

    def close(self):
        """Clean up resources."""
        try:
            self.driver.quit()
        except Exception as e:
            self.logger.error(f"Error closing driver: {str(e)}")

def read_names_from_file(file_path: Path) -> List[str]:
    """Read names from file, skipping empty lines and stripping whitespace."""
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        logging.error(f"Error reading names from file: {str(e)}")
        return []

def read_info(file_path):
    info = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):  # Ignore empty lines and comments
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()
    return info

def main():
    parser = argparse.ArgumentParser(description="Web automation tool for managing configurations.")
    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")

    # Add subparsers
    add_list = subparsers.add_parser('add-list', help="Add names from a file")
    add_list.add_argument('filename', type=Path, help="Path to file containing names")

    add_one = subparsers.add_parser('add-one', help="Add a single name")
    add_one.add_argument('name', help="Name to add")

    download_list = subparsers.add_parser('download-list', help="Download configurations from file")
    download_list.add_argument('filename', type=Path, help="Path to file containing names")

    download_one = subparsers.add_parser('download-one', help="Download single configuration")
    download_one.add_argument('name', help="Name to download")

    args = parser.parse_args()


    info = read_info('info.txt')
    url = f"http://{info['IP']}:51821/"
    password = info['password']

    config = Config(url=url, password=password)
    automation = WebAutomation(config)

    try:
        if args.mode in ['add-list', 'download-list']:
            names = read_names_from_file(args.filename)
            if not names:
                automation.logger.error("No valid names found in file")
                return
            operation = 'add' if args.mode == 'add-list' else 'download'
            automation.process_name_list(names, operation)
        
        elif args.mode == 'add-one':
            automation.add_name(args.name)
        
        elif args.mode == 'download-one':
            automation.download_configuration(args.name)
        
        else:
            parser.print_help()

    finally:
        automation.close()

if __name__ == "__main__":
    main()
