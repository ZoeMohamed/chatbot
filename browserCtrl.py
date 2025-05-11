from PyQt5.QtCore import pyqtSignal, QThread
from selenium import webdriver
import json
import os
import platform
import time
import random
import pyperclip
import subprocess
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from subprocess import CREATE_NO_WINDOW
import chromedriver_autoinstaller
from appLog import log


try:
    log.info("browserCTRL start to dl")
    chromedriver_autoinstaller.install()
except:
    log.exception("")
CHROME = 1
FIREFOX = 2


class Web(QThread):
    __URL = "https://web.whatsapp.com/"
    driverNum = 0
    lcdNumber_reviewed = pyqtSignal(int)
    lcdNumber_nwa = pyqtSignal(int)
    lcdNumber_wa = pyqtSignal(int)
    LogBox = pyqtSignal(str)
    wa = pyqtSignal(str)
    nwa = pyqtSignal(str)
    EndWork = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        counter_start=0,
        step="A",
        numList=None,
        sleepMin=3,
        sleepMax=6,
        text="",
        path="",
        Remember=False,
        browser=1,
    ):
        super(Web, self).__init__(parent)
        self.counter_start = counter_start
        self.Numbers = numList
        self.step = step
        self.sleepMin = sleepMin
        self.sleepMax = sleepMax
        self.text = text
        self.path = path
        self.remember = Remember
        self.isRunning = True
        try:
            if not os.path.exists("./temp/cache"):
                os.makedirs("temp/cache/")
        except:
            os.makedirs("./temp/cache/")
        # Save Session Section
        self.__platform = platform.system().lower()
        if self.__platform != "windows" and self.__platform != "linux":
            raise OSError("Only Windows and Linux are supported for now.")

        self.__browser_choice = 0
        self.__browser_options = None
        self.__browser_user_dir = None
        self.__driver = None
        self.service = Service()
        self.service.creation_flags = CREATE_NO_WINDOW
        if browser == 1:
            self.set_browser(CHROME)
        elif browser == 2:
            self.set_browser(FIREFOX)

        self.__init_browser()

    def driverBk(self):
        option = webdriver.ChromeOptions()
        option.add_argument("--disable-notifications")
        # option.add_argument(fr"--user-data-dir={userDataPath}")
        try:
            try:
                self.__driver = webdriver.Chrome(options=option, service=self.service)
                log.debug("webDriver")
            except:
                log.exception("error remeber")
                self.__driver = webdriver.Chrome(service=self.service)
        except:
            log.exception("Chrome ->:")
            # if not os.path.exists('temp/F.Options'):
            #     os.mkdir('temp/F.Options')
            # optionsF = webdriver.FirefoxOptions()
            # optionsF.add_argument('-headless')  ## hidden Browser
            try:
                self.__driver = webdriver.Firefox()
            except:
                pass
        try:
            self.__driver.set_window_position(0, 0)
            self.__driver.set_window_size(1080, 840)
        except:
            pass

    def is_logged_in(self):
        status = self.__driver.execute_script(
            "if (document.querySelector('*[data-icon=new-chat-outline]') !== null) { return true } else { return false }"
        )
        return status

    def copyToClipboard(self, text):
        try:  # Copy Text To clipboard
            try:
                subprocess.run("pbcopy", universal_newlines=True, input=text)
            except Exception:
                pyperclip.copy(text)
        except Exception:
            subprocess.run("pbcopy", universal_newlines=True, input=text)
        finally:
            pyperclip.copy(text)

    def take_debug_screenshot(self, name="debug"):
        """Take a screenshot for debugging purposes"""
        try:
            if not os.path.exists("./temp/screenshots"):
                os.makedirs("./temp/screenshots")
            filename = f"./temp/screenshots/{name}_{int(time.time())}.png"
            self.__driver.save_screenshot(filename)
            log.debug(f"Screenshot saved as {filename}")
        except Exception as e:
            log.debug(f"Failed to take screenshot: {str(e)}")

    def send_image_js(self, image_path, caption_text=""):
        """Send an image using JavaScript for better compatibility with WhatsApp Web UI changes"""
        try:
            # Step 1: Ensure focus is on the main chat panel, away from any search boxes.
            self.__driver.execute_script(
                """
                const mainChatPanel = document.querySelector('div[data-testid="conversation-panel-body"]');
                if (mainChatPanel) {
                    mainChatPanel.click();
                } else {
                    const appElement = document.querySelector('div#app .two');
                    if (appElement) appElement.click();
                }
                if (document.activeElement && document.activeElement.getAttribute('aria-label')?.toLowerCase().includes('search')) {
                    document.activeElement.blur();
                }
            """
            )
            time.sleep(0.5)  # Short pause for focus to settle
            self.take_debug_screenshot("1_chat_area_focused")

            # Step 2: Click on attachment button
            clip_clicked = self.__driver.execute_script(
                """
                const clipSelectors = [
                    '[data-testid="attach-menu-plus"]',
                    '[data-testid="clip"]',
                    '[title="Attach"]',
                    'span[data-icon="attach-menu-plus"]',
                    'span[data-icon="clip"]',
                    '[aria-label="Attach"]'
                ];
                for (const selector of clipSelectors) {
                    const button = document.querySelector(selector);
                    if (button) { button.click(); return `Clicked clip: ${selector}`; }
                }
                const allButtons = document.querySelectorAll('[role="button"]');
                for (const btn of allButtons) {
                    if ((btn.getAttribute('aria-label') || '').toLowerCase().includes('attach') ||
                        (btn.title || '').toLowerCase().includes('attach') ||
                        btn.querySelector('span[data-icon="clip"], span[data-icon="attach-menu-plus"]')) {
                        btn.click(); return 'Clicked generic attach button';
                    }
                }
                return 'Failed to click attachment button';
            """
            )
            log.debug(f"Attachment click result: {clip_clicked}")
            if not clip_clicked or clip_clicked.startswith("Failed"):
                self.take_debug_screenshot("error_clip_click_failed")
                return False
            time.sleep(1.5)  # Increased wait for menu to open fully
            self.take_debug_screenshot("2_attachment_menu_opened")

            # Step 3: Select the "Photos & videos" option specifically
            photo_option_clicked = self.__driver.execute_script(
                """
                // Try to find the main attachment menu list
                const menuPopup = document.querySelector('div[data-testid="attach-menu-popup"], div[aria-label*="Attach"][role="dialog"], div[aria-labelledby*="attach"][role="listbox"], ul[role="menu"], div[role="application"] ul');
                let potentialMenuItems = [];
                if (menuPopup) {
                    potentialMenuItems = Array.from(menuPopup.querySelectorAll('li[role="menuitem"], div[role="menuitem"], button[role="menuitem"], div[role="button"][aria-label]'));
                } else {
                    // Broader search if specific menu popup not found
                    potentialMenuItems = Array.from(document.querySelectorAll('div[role="dialog"] [role="menuitem"], div[role="listbox"] [role="option"], [aria-label*="Attach"] [role="menuitem"], [aria-label*="Attach"] [role="button"]'));
                }

                if (potentialMenuItems.length === 0) {
                    return 'Failed: No potential menu items found initially by common selectors.';
                }

                // Filter out items that are definitely sticker-related early
                const items = potentialMenuItems.filter(item => {
                    const text = (item.textContent || item.innerText || item.getAttribute('aria-label') || '').toLowerCase();
                    const html = item.outerHTML.toLowerCase();
                    return !text.includes('sticker') && !html.includes('sticker') && !item.closest('[aria-label*="sticker" i]');
                });

                if (items.length === 0) {
                    return 'Failed: No non-sticker menu items found after filtering.';
                }

                // Priority 1: Text content check (more flexible)
                const photoKeywords = ['photos & videos', 'photos and videos', 'fotos e vídeos', 'fotos y videos', 'gallery', 'bilder und videos', 'photos et vidéos'];
                for (const item of items) {
                    const text = (item.textContent || item.innerText || item.getAttribute('aria-label') || '').trim().toLowerCase();
                    const html = item.outerHTML.toLowerCase(); // Re-check for safety

                    if (photoKeywords.some(keyword => text.includes(keyword)) && !text.includes('sticker') && !html.includes('sticker')) {
                        const stickerIcon = item.querySelector('span[data-icon*="sticker"], svg[aria-label*="sticker" i]');
                        const newStickerText = item.querySelector('span[data-testid="new-sticker-text"]'); // Example of specific sticker element text
                        if (!stickerIcon && !newStickerText) {
                             item.click();
                             return `Clicked P1 (text): ${text.substring(0, 30)}`;
                        }
                    }
                }

                // Priority 2: Specific attribute selectors (aria-label, data-testid, title)
                const specificPhotoSelectors = [
                    '[aria-label*="Photos & videos" i]',
                    '[aria-label*="Photos and videos" i]',
                    '[aria-label*="fotos y videos" i]',
                    '[aria-label*="fotos e vídeos" i]',
                    '[aria-label*="Bilder und Videos" i]',
                    '[aria-label*="Photos et vidéos" i]',
                    '[data-testid="mi-attach-media"]',
                    '[data-testid="attach-image"]',
                    '[data-testid="photos-videos"]', // Matches the list item itself
                    'button[title*="Photos & videos" i]',
                    'div[title*="Photos & videos" i]'
                ];

                for (const selector of specificPhotoSelectors) {
                    for (const item of items) { // Search within already filtered, visible items
                        if (item.matches(selector) || (item.querySelector(selector) && item.querySelector(selector).offsetParent !== null) ) {
                            const elToClick = item.matches(selector) ? item : item.querySelector(selector);
                            const text = (elToClick.textContent || elToClick.innerText || elToClick.getAttribute('aria-label') || '').toLowerCase();
                            const html = elToClick.outerHTML.toLowerCase();
                            if (!text.includes('sticker') && !html.includes('sticker')) {
                                elToClick.click();
                                return `Clicked P2 (specific selector on item): ${selector}`;
                            }
                        }
                    }
                    // Fallback: query document for very specific selectors if not found in items
                    if (selector.includes('data-testid') || selector.includes('aria-label')) {
                         const elem = document.querySelector(selector);
                         if (elem && elem.offsetParent !== null) { // Check visibility
                            const text = (elem.textContent || elem.innerText || elem.getAttribute('aria-label') || '').toLowerCase();
                            const html = elem.outerHTML.toLowerCase();
                            if (!text.includes('sticker') && !html.includes('sticker')) {
                                elem.click();
                                return `Clicked P2 (specific global selector): ${selector}`;
                            }
                         }
                    }
                }

                // Priority 3: Icon check + associated text (NO sticker)
                const photoIconSelectors = [
                    'span[data-icon="gallery"]', 
                    'span[data-icon="image"]', 
                    'span[data-icon="photo"]', 
                    'span[data-icon="photos-videos"]',
                    'span[data-icon="photos-videos-filled"]',
                    'span[data-icon="landscape"]',
                    'svg[aria-label*="photo" i], svg[aria-label*="image" i], svg[aria-label*="gallery" i]'
                ];
                for (const item of items) {
                    let hasCorrectIcon = false;
                    for (const iconSel of photoIconSelectors) {
                        if (item.querySelector(iconSel)) {
                            hasCorrectIcon = true; break;
                        }
                    }
                    if (hasCorrectIcon) {
                        const text = (item.textContent || item.innerText || item.getAttribute('aria-label') || '').toLowerCase();
                        const html = item.outerHTML.toLowerCase();
                        if ((text.includes('photo') || text.includes('video') || text.includes('gallery')) && 
                            !text.includes('sticker') && !html.includes('sticker')) {
                            item.click();
                            return `Clicked P3 (icon & text): ${text.substring(0, 30)}`;
                        }
                    }
                }

                // Priority 4: Positional attempt (e.g., second item if it matches criteria)
                // The image shows "Photos & videos" as the second item.
                if (items.length > 1) {
                    const secondItem = items[1]; // Second item from the *filtered* list
                    if (secondItem) {
                        const text = (secondItem.textContent || secondItem.innerText || secondItem.getAttribute('aria-label') || '').toLowerCase();
                        const html = secondItem.outerHTML.toLowerCase();
                        const photoRelatedText = photoKeywords.some(keyword => text.includes(keyword));
                        const hasMediaIcon = photoIconSelectors.some(iconSel => secondItem.querySelector(iconSel));
                        const notOtherKnownItems = !text.includes('document') && !text.includes('camera') && !text.includes('poll') && !text.includes('contact');

                        if (photoRelatedText && hasMediaIcon && notOtherKnownItems && !text.includes('sticker') && !html.includes('sticker')) {
                            secondItem.click();
                            return `Clicked P4 (positional [1] with checks): ${text.substring(0,30)}`;
                        }
                    }
                }
                return 'Failed: All strategies exhausted for Photos & Videos.';
                """
            )
            log.debug(f"Photo option click result: {photo_option_clicked}")
            if not photo_option_clicked or photo_option_clicked.startswith("Failed"):
                self.take_debug_screenshot("error_photo_option_click_failed")
                return False
            time.sleep(1.5)
            self.take_debug_screenshot("3_photo_option_clicked_or_input_ready")

            # Step 4: Handle file input using its specific accept attributes
            image_path_abs = os.path.abspath(image_path)
            log.debug(f"Attempting to send keys for image: {image_path_abs}")

            file_sent_successfully = False
            # Primary target: input[type="file"] specifically for images/videos
            # This input might have been revealed by clicking "Photos & Videos"
            file_input_selectors = [
                'input[type="file"][accept*="image/*,video/*"]',
                'input[type="file"][accept*="image/*"][accept*="video/*"]',
                'input[type="file"][accept*="image/*"]',  # If only image is fine
                # Fallback to any file input if specific ones aren't found after clicking Photos & Videos
                'input[type="file"]',
            ]

            for selector in file_input_selectors:
                try:
                    # Ensure the input is visible and enabled
                    self.__driver.execute_script(
                        f"""
                        const input = document.querySelector('{selector}');
                        if (input) {{
                            input.style.display = 'block';
                            input.style.visibility = 'visible';
                            input.style.opacity = '1';
                            input.style.width = 'auto'; // Reset styles that might hide it
                            input.style.height = 'auto';
                            input.style.position = 'static';
                            input.style.clip = 'auto'; // Ensure it's not clipped
                        }}
                    """
                    )
                    time.sleep(0.2)  # Brief pause for style changes

                    file_inputs = self.__driver.find_elements(By.CSS_SELECTOR, selector)
                    for file_input_element in file_inputs:
                        if (
                            file_input_element.is_displayed()
                            and file_input_element.is_enabled()
                        ):
                            log.debug(
                                f"Found interactable file input with selector: {selector}"
                            )
                            file_input_element.send_keys(image_path_abs)
                            log.debug(f"Sent keys to file input: {image_path_abs}")
                            file_sent_successfully = True
                            break  # Break from inner loop once keys are sent
                        else:
                            log.debug(
                                f"File input ({selector}) found but not interactable (Displayed: {file_input_element.is_displayed()}, Enabled: {file_input_element.is_enabled()})."
                            )
                    if file_sent_successfully:
                        break  # Break from outer loop if successful
                except Exception as e:
                    log.debug(f"Error with file input selector '{selector}': {str(e)}")

            if not file_sent_successfully:
                log.error(
                    "All attempts to find and send keys to a suitable file input failed."
                )
                self.take_debug_screenshot("error_file_input_send_keys_failed")
                return False

            time.sleep(4)  # Wait for image to upload and preview
            self.take_debug_screenshot("4_image_uploaded_preview")

            # Step 5: Set caption if provided
            if caption_text and caption_text.strip():
                caption_escaped = (
                    caption_text.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                )
                caption_set_result = self.__driver.execute_script(
                    f"""
                    const captionSelectors = [
                        'div[data-testid="media-caption-input"] [role="textbox"]',
                        'div[aria-label*="caption"][role="textbox"]', // More general caption aria-label
                        'div[data-lexical-editor="true"][role="textbox"]',
                        'textarea[aria-label*="caption"]'
                    ];
                    for (const selector of captionSelectors) {{
                        const captionBox = document.querySelector(selector);
                        if (captionBox && captionBox.offsetParent !== null) {{ // Check visibility
                            captionBox.focus();
                            captionBox.innerHTML = '{caption_escaped}';
                            captionBox.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return `Set caption using: ${{selector}}`;
                        }}
                    }}
                    // Fallback: find any contenteditable in the preview footer/area
                    const previewArea = document.querySelector('div[data-testid="media-preview-modal-body"]') || document.querySelector('div[data-testid="media-preview-modal-footer"]') || document.body;
                    const editables = previewArea.querySelectorAll('div[contenteditable="true"], textarea');
                    for (let i = editables.length - 1; i >= 0; i--) {{ // Prioritize last ones
                        const box = editables[i];
                        if (box.offsetParent !== null && !box.getAttribute('aria-label')?.toLowerCase().includes('search')){{
                             box.focus();
                             box.innerHTML = '{caption_escaped}';
                             box.dispatchEvent(new Event('input', {{ bubbles: true }}));
                             return 'Set caption using fallback editable';
                        }}
                    }}
                    return 'Failed to set caption';
                """
                )
                log.debug(f"Caption set result: {caption_set_result}")
                if not caption_set_result or caption_set_result.startswith("Failed"):
                    self.take_debug_screenshot("warning_caption_set_failed")
                time.sleep(0.5)

            self.take_debug_screenshot("5_before_sending_image")

            # Step 6: Click send button
            send_button_clicked = self.__driver.execute_script(
                """
                const sendSelectors = [
                    'button[data-testid="send"] > span[data-icon="send"]',
                    'button[data-testid="send"]',
                    'div[aria-label="Send"] span[data-icon="send"]',
                    'button[aria-label="Send"]',
                    'span[data-icon="send-light"]',
                    'div[role="button"][title="Send"] span[data-icon="send"]'
                ];
                for (const selector of sendSelectors) {
                    const button = document.querySelector(selector);
                    // Check if button is visible and interactable
                    if (button && button.offsetParent !== null && !button.disabled) {
                        button.click();
                        return `Clicked send button: ${selector}`;
                    }
                }
                // Fallback for send button in media preview footer
                const footer = document.querySelector('div[data-testid="media-preview-modal-footer"]');
                if (footer) {
                    const sendButton = footer.querySelector('button span[data-icon="send"], button[aria-label="Send"]');
                     if (sendButton && sendButton.offsetParent !== null && !sendButton.disabled) {
                        sendButton.click();
                        return 'Clicked send button in footer (fallback)';
                    }
                }
                return 'Failed to click send button';
                """
            )
            log.debug(f"Send button click result: {send_button_clicked}")

            if not send_button_clicked or send_button_clicked.startswith("Failed"):
                log.warning(
                    "Failed to click send button via JS, attempting Enter key press as a last resort."
                )
                self.take_debug_screenshot("error_send_button_js_failed")
                try:
                    # Attempt to send Enter to the most relevant active element or caption box
                    focused_element_script = """
                    let target = document.activeElement;
                    if (!target || target === document.body || target === document.documentElement) {
                        // If no specific focus, try the caption box
                        target = document.querySelector('div[data-testid="media-caption-input"] [role="textbox"], div[aria-label*="caption"][role="textbox"]');
                    }
                    if (target && typeof target.dispatchEvent === 'function') {
                         // Simulate Enter key press more reliably
                        const enterDown = new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true});
                        const enterUp = new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true});
                        target.dispatchEvent(enterDown);
                        target.dispatchEvent(enterUp);
                        return true; // Assume Enter was sent
                    }
                    return false;
                    """
                    enter_sent = self.__driver.execute_script(focused_element_script)

                    if enter_sent:
                        log.debug("Successfully dispatched Enter key event via JS.")
                        send_button_clicked = "Sent Enter key via JS"  # Mark as success
                    else:
                        # Fallback to Selenium's active element if JS dispatch fails
                        active_el = self.__driver.switch_to.active_element
                        if active_el and active_el.tag_name not in ["body", "html"]:
                            active_el.send_keys(Keys.RETURN)
                            log.debug("Sent RETURN key to active Selenium element.")
                            send_button_clicked = (
                                "Sent Enter key via Selenium"  # Mark as success
                            )
                        else:
                            log.error(
                                "Enter key fallback failed: No suitable active element."
                            )
                            self.take_debug_screenshot("error_enter_key_send_failed")
                            return False  # Definitively failed
                except Exception as e_enter:
                    log.error(f"Exception during Enter key fallback: {str(e_enter)}")
                    self.take_debug_screenshot("error_enter_key_exception")
                    return False  # Definitively failed

            time.sleep(2.5)  # Wait for message to actually send
            self.take_debug_screenshot("6_after_sending_attempt")

            # Check if the send operation was successful (not starting with "Failed")
            return not (
                isinstance(send_button_clicked, str)
                and send_button_clicked.startswith("Failed")
            )

        except Exception as e:
            log.exception(f"General error in send_image_js: {str(e)}")
            self.take_debug_screenshot("error_send_image_js_general_exception")
            return False

    def ANALYZ(self):
        try:
            log.debug("analyz")
            if self.remember:
                log.debug("remember")
                cacheList = os.listdir("temp/cache/")
                if len(cacheList) != 0:
                    self.access_by_file(f"./temp/cache/{cacheList[0]}")
                    log.debug("recover")
                else:
                    self.driverBk()
                    self.__driver.get(self.__URL)
            else:
                log.debug("! remember !")
                self.driverBk()
                self.__driver.get(self.__URL)

            while True:
                log.debug("Login Check")
                time.sleep(1)
                if self.is_logged_in():
                    log.debug("login")
                    logtxt = "Login Success"
                    self.LogBox.emit(logtxt)
                    break
            log.debug("thread:", self.counter_start)
            i = 0
            f = 0
            nf = 0
            for num in self.Numbers:
                logtxt = ""
                try:
                    time.sleep(3)
                    if i == 0:
                        execu = f"""
                                var a = document.createElement('a');
                                var link = document.createTextNode("hiding");
                                a.appendChild(link);
                                a.href = "https://wa.me/{num}";
                                document.head.appendChild(a);
                                """
                        try:
                            self.__driver.execute_script(execu)
                        except:
                            log.exception("error")
                    else:
                        element = self.__driver.find_element(By.XPATH, "/html/head/a")
                        self.__driver.execute_script(
                            f"arguments[0].setAttribute('href','https://wa.me/{num}');",
                            element,
                        )
                    user = self.__driver.find_element(By.XPATH, "/html/head/a")
                    self.__driver.execute_script("arguments[0].click();", user)
                    time.sleep(2)
                    sourceWeb = self.__driver.page_source
                    if "Phone number shared via url is invalid" in sourceWeb:
                        log.debug(f"Not Found {num}")
                        nf += 1
                        self.lcdNumber_nwa.emit(nf)
                        logtxt = f"Number::{num} => Not Find!"
                        self.nwa.emit(f"{num}")
                    else:
                        log.debug(f"find {num}")
                        f += 1
                        self.lcdNumber_wa.emit(f)
                        logtxt = f"Number::{num} => Find."
                        self.wa.emit(f"{num}")
                except:
                    logtxt = f"Number::{num} Error !"
                    continue
                finally:
                    i += 1
                    log.debug(i)
                    self.lcdNumber_reviewed.emit(i)
                    self.LogBox.emit(logtxt)
            time.sleep(2)
            log.debug("end")
            self.EndWork.emit("-- analysis completed --")
            self.isRunning = False
            self.__driver.quit()
        except:
            log.exception("Analyz ->:")

    def SendTEXT(self):
        log.debug("sent text")
        if self.remember:
            cacheList = os.listdir("temp/cache/")
            if len(cacheList) != 0:
                self.access_by_file(f"./temp/cache/{cacheList[0]}")
                log.debug("recover")
            else:
                self.driverBk()
                self.__driver.get(self.__URL)
        else:
            self.driverBk()
            self.__driver.get(self.__URL)
        time.sleep(2)
        while True:
            time.sleep(1)
            if self.is_logged_in():
                log.debug("login")
                logtxt = "Login Success"
                self.LogBox.emit(logtxt)
                break
        i = 0
        f = 0
        nf = 0
        from random import randint

        log.debug(self.Numbers)
        for num in self.Numbers:
            logtxt = ""
            try:
                time.sleep(3)
                if i == 0:
                    execu = f"""
                            var a = document.createElement('a');
                            var link = document.createTextNode("hiding");
                            a.appendChild(link);
                            a.href = "https://wa.me/{num}";
                            document.head.appendChild(a);
                            """
                    try:
                        self.__driver.execute_script(execu)
                    except:
                        log.exception("error")
                        logtxt = "ERROR !"
                        break
                else:
                    element = self.__driver.find_element(By.XPATH, "/html/head/a")
                    self.__driver.execute_script(
                        f"arguments[0].setAttribute('href','https://wa.me/{num}');",
                        element,
                    )
                user = self.__driver.find_element(By.XPATH, "/html/head/a")
                self.__driver.execute_script("arguments[0].click();", user)
                time.sleep(2)
                sourceWeb = self.__driver.page_source
                if "Phone number shared via url is invalid" in sourceWeb:
                    log.debug(f"Not Found {num}")
                    nf += 1
                    self.lcdNumber_nwa.emit(nf)
                    logtxt = f"Number::{num} => No Send!"
                    self.nwa.emit(f"{num}")
                else:
                    log.debug(f"find {num}")
                    time.sleep(2)
                    try:
                        # Wait for chat to be fully loaded - WhatsApp takes time to show the message field
                        time.sleep(5)

                        # Try to locate the message input field using various selectors in order of specificity
                        try:
                            # Latest WhatsApp Web - main message input
                            textBox = self.__driver.find_element(
                                By.XPATH,
                                '//div[@contenteditable="true" and @data-tab="10"]',
                            )
                            log.debug(
                                "Found message input using contenteditable data-tab selector"
                            )
                        except Exception:
                            try:
                                # Alternative selector for message input in WhatsApp Web
                                textBox = self.__driver.find_element(
                                    By.XPATH,
                                    '//div[@role="textbox" and @contenteditable="true" and @title="Type a message"]',
                                )
                                log.debug(
                                    "Found message input using textbox role selector"
                                )
                            except Exception:
                                try:
                                    # Look for footer with the message input
                                    textBox = self.__driver.find_element(
                                        By.XPATH,
                                        '//footer//div[@contenteditable="true"]',
                                    )
                                    log.debug(
                                        "Found message input using footer div selector"
                                    )
                                except Exception:
                                    # Most general selector - any editable div in the chat area
                                    textBox = self.__driver.find_element(
                                        By.XPATH,
                                        '//div[contains(@class,"copyable-text") and @contenteditable="true"]',
                                    )
                                    log.debug(
                                        "Found message input using copyable-text class selector"
                                    )

                        # Make sure we're focused on the text input
                        self.__driver.execute_script("arguments[0].click();", textBox)
                        time.sleep(1)

                        # Send the message
                        self.copyToClipboard(self.text)
                        textBox.send_keys(Keys.CONTROL, "v")
                        time.sleep(1)

                        # Try to send the message
                        try:
                            # Look for a send button first
                            send_button = self.__driver.find_element(
                                By.XPATH, '//span[@data-icon="send"]'
                            )
                            send_button.click()
                        except Exception:
                            # Fall back to keyboard shortcuts
                            try:
                                textBox.send_keys(Keys.RETURN)
                            except Exception:
                                textBox.send_keys(Keys.ENTER)

                        time.sleep(1)
                        f += 1
                        self.lcdNumber_wa.emit(f)
                        logtxt = f"Number::{num} => Sent."
                        self.wa.emit(f"{num}")
                    except Exception as e:
                        log.exception(f"Error with text input for {num}: {str(e)}")
                        logtxt = f"Error sending to {num}: Input field not found"

                time.sleep(randint(self.sleepMin, self.sleepMax))
            except Exception as e:
                log.exception(f"General error with {num}: {str(e)}")
                logtxt = f"Error To Number = {num} "
            finally:
                i += 1
                self.lcdNumber_reviewed.emit(i)
                self.LogBox.emit(logtxt)
        log.debug("end msg")
        self.EndWork.emit("-- Send Message completed --")
        self.stop()
        self.isRunning = False

    def SendIMG(self):
        log.debug("sent img")
        if self.remember:
            cacheList = os.listdir("temp/cache/")
            if len(cacheList) != 0:
                self.access_by_file(f"./temp/cache/{cacheList[0]}")
                log.debug("recover")
            else:
                self.driverBk()
                self.__driver.get(self.__URL)
        else:
            self.driverBk()
            self.__driver.get(self.__URL)
        time.sleep(2)
        while True:
            time.sleep(1)
            if self.is_logged_in():
                log.debug("login")
                logtxt = "Login Success"
                self.LogBox.emit(logtxt)
                break
        i = 0
        f = 0
        nf = 0
        from random import randint

        log.debug(self.Numbers)
        for num in self.Numbers:
            log.debug(num)
            logtxt = ""
            try:
                time.sleep(3)
                if i == 0:
                    execu = f"""
                            var a = document.createElement('a');
                            var link = document.createTextNode("hiding");
                            a.appendChild(link);
                            a.href = "https://wa.me/{num}";
                            document.head.appendChild(a);
                            """
                    try:
                        self.__driver.execute_script(execu)
                    except:
                        log.exception("error img")
                        logtxt = "ERROR !"
                        break
                else:
                    element = self.__driver.find_element(By.XPATH, "/html/head/a")
                    self.__driver.execute_script(
                        f"arguments[0].setAttribute('href','https://wa.me/{num}');",
                        element,
                    )
                user = self.__driver.find_element(By.XPATH, "/html/head/a")
                self.__driver.execute_script("arguments[0].click();", user)
                time.sleep(2)
                sourceWeb = self.__driver.page_source
                if "Phone number shared via url is invalid" in sourceWeb:
                    log.debug(f"Not Found {num}")
                    nf += 1
                    self.lcdNumber_nwa.emit(nf)
                    logtxt = f"Number::{num} => No Send"
                    self.nwa.emit(f"{num}")
                else:
                    log.debug(f"find {num}")
                    time.sleep(3)  # Extra time to ensure chat is loaded

                    # Use the new JavaScript-based image sending method
                    if self.send_image_js(self.path, self.text):
                        f += 1
                        self.lcdNumber_wa.emit(f)
                        logtxt = f"Number::{num} => Sent"
                        self.wa.emit(f"{num}")
                    else:
                        log.debug(f"Failed to send image to {num}")
                        logtxt = f"Error sending image to {num}"

                time.sleep(randint(self.sleepMin, self.sleepMax))
            except Exception as e:
                log.exception(f"Error sending message to {num}: {str(e)}")
                logtxt = f"Error To Number = {num} "
                continue
            finally:
                i += 1
                self.lcdNumber_reviewed.emit(i)
                self.LogBox.emit(logtxt)

        log.debug("end msg")
        self.EndWork.emit("-- Send Image completed --")
        self.stop()
        self.isRunning = False

    def addAcc(self):
        try:
            log.debug("Add Account")
            if self.remember:
                if self.path == "":
                    cacheName = str(random.randint(1, 9999999))
                    self.path = cacheName
                self.save_profile(
                    self.get_active_session(), f"./temp/cache/{self.path}"
                )
                log.debug("File saved.")
            log.debug("thread:", self.counter_start)
            self.EndWork.emit("-- Add Account completed --")
            self.isRunning = False
        except:
            log.exception("Add Account ->:")

    def run(self):
        while self.isRunning == True:
            if self.step == "A":
                self.ANALYZ()
            elif self.step == "M":
                self.SendTEXT()
            elif self.step == "I":
                self.SendIMG()
            elif self.step == "Add":
                self.addAcc()

    def stop(self):
        self.isRunning = False
        log.debug("stopping thread...")
        try:
            self.__driver.quit()
        except:
            pass
        # self.terminate()

    def __init_browser(self):
        if self.__browser_choice == CHROME:
            self.__browser_options = webdriver.ChromeOptions()

            if self.__platform == "windows":
                self.__browser_user_dir = os.path.join(
                    os.environ["USERPROFILE"],
                    "Appdata",
                    "Local",
                    "Google",
                    "Chrome",
                    "User Data",
                )
            elif self.__platform == "linux":
                self.__browser_user_dir = os.path.join(
                    os.environ["HOME"], ".config", "google-chrome"
                )

        elif self.__browser_choice == FIREFOX:
            self.__browser_options = webdriver.FirefoxOptions()

            if self.__platform == "windows":
                self.__browser_user_dir = os.path.join(
                    os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles"
                )
                self.__browser_profile_list = os.listdir(self.__browser_user_dir)
            elif self.__platform == "linux":
                self.__browser_user_dir = os.path.join(
                    os.environ["HOME"], ".mozilla", "firefox"
                )

        self.__browser_options.headless = True
        self.__refresh_profile_list()

    def __refresh_profile_list(self):
        if self.__browser_choice == CHROME:
            self.__browser_profile_list = [""]
            for profile_dir in os.listdir(self.__browser_user_dir):
                if "profile" in profile_dir.lower():
                    if profile_dir != "System Profile":
                        self.__browser_profile_list.append(profile_dir)
        elif self.__browser_choice == FIREFOX:
            # TODO: consider reading out the profiles.ini
            self.__browser_profile_list = []
            for profile_dir in os.listdir(self.__browser_user_dir):
                if not profile_dir.endswith(".default"):
                    if os.path.isdir(
                        os.path.join(self.__browser_user_dir, profile_dir)
                    ):
                        self.__browser_profile_list.append(profile_dir)

    def __get_indexed_db(self):
        self.__driver.execute_script(
            "window.waScript = {};"
            "window.waScript.waSession = undefined;"
            "function getAllObjects() {"
            'window.waScript.dbName = "wawc";'
            'window.waScript.osName = "user";'
            "window.waScript.db = undefined;"
            "window.waScript.transaction = undefined;"
            "window.waScript.objectStore = undefined;"
            "window.waScript.getAllRequest = undefined;"
            "window.waScript.request = indexedDB.open(window.waScript.dbName);"
            "window.waScript.request.onsuccess = function(event) {"
            "window.waScript.db = event.target.result;"
            "window.waScript.transaction = window.waScript.db.transaction("
            "window.waScript.osName);"
            "window.waScript.objectStore = window.waScript.transaction.objectStore("
            "window.waScript.osName);"
            "window.waScript.getAllRequest = window.waScript.objectStore.getAll();"
            "window.waScript.getAllRequest.onsuccess = function(getAllEvent) {"
            "window.waScript.waSession = getAllEvent.target.result;"
            "};"
            "};"
            "}"
            "getAllObjects();"
        )
        while not self.__driver.execute_script(
            "return window.waScript.waSession != undefined;"
        ):
            time.sleep(1)
        wa_session_list = self.__driver.execute_script(
            "return window.waScript.waSession;"
        )
        return wa_session_list

    def __get_profile_storage(self, profile_name=None):
        self.__refresh_profile_list()

        if profile_name is not None and profile_name not in self.__browser_profile_list:
            raise ValueError(
                "The specified profile_name was not found. Make sure the name is correct."
            )

        if profile_name is None:
            self.__start_visible_session()
        else:
            self.__start_invisible_session(profile_name)

        indexed_db = self.__get_indexed_db()

        self.__driver.quit()

        return indexed_db

    def __start_session(self, options, profile_name=None, wait_for_login=True):
        if profile_name is None:
            if self.__browser_choice == CHROME:
                self.__driver = webdriver.Chrome(
                    options=options,
                    service_args=[
                        "hide_console",
                    ],
                    service=self.service,
                )
                self.__driver.set_window_position(0, 0)
                self.__driver.set_window_size(670, 800)
            elif self.__browser_choice == FIREFOX:
                self.__driver = webdriver.Firefox(options=options)

            self.__driver.get(self.__URL)

            if wait_for_login:
                verified_wa_profile_list = False
                while not verified_wa_profile_list:
                    time.sleep(1)
                    verified_wa_profile_list = False
                    for object_store_obj in self.__get_indexed_db():
                        if "WASecretBundle" in object_store_obj["key"]:
                            verified_wa_profile_list = True
                            break
        else:
            if self.__browser_choice == CHROME:
                options.add_argument(
                    "user-data-dir=%s"
                    % os.path.join(self.__browser_user_dir, profile_name)
                )
                self.__driver = webdriver.Chrome(
                    options=options,
                    service_args=[
                        "hide_console",
                    ],
                    service=self.service,
                )
            elif self.__browser_choice == FIREFOX:
                fire_profile = webdriver.FirefoxProfile(
                    os.path.join(self.__browser_user_dir, profile_name)
                )
                self.__driver = webdriver.Firefox(fire_profile, options=options)

            self.__driver.get(self.__URL)

    def __start_visible_session(self, profile_name=None, wait_for_login=True):
        options = self.__browser_options
        options.headless = False
        self.__refresh_profile_list()

        if profile_name is not None and profile_name not in self.__browser_profile_list:
            raise ValueError(
                "The specified profile_name was not found. Make sure the name is correct."
            )

        self.__start_session(options, profile_name, wait_for_login)

    def __start_invisible_session(self, profile_name=None):
        self.__refresh_profile_list()
        if profile_name is not None and profile_name not in self.__browser_profile_list:
            raise ValueError(
                "The specified profile_name was not found. Make sure the name is correct."
            )

        self.__start_session(self.__browser_options, profile_name)

    def set_browser(self, browser):
        if type(browser) == str:
            if browser.lower() == "chrome":
                self.__browser_choice = CHROME
            elif browser.lower() == "firefox":
                self.__browser_choice = FIREFOX
            else:
                raise ValueError(
                    'The specified browser is invalid. Try to use "chrome" or "firefox" instead.'
                )
        else:
            if browser == CHROME:
                pass
            elif browser == FIREFOX:
                pass
            else:
                raise ValueError(
                    "Browser type invalid. Try to use WaWebSession.CHROME or WaWebSession.FIREFOX instead."
                )

            self.__browser_choice = browser

    def get_active_session(self, use_profile=None):
        profile_storage_dict = {}
        use_profile_list = []
        self.__refresh_profile_list()

        if use_profile and use_profile not in self.__browser_profile_list:
            raise ValueError("Profile does not exist: %s", use_profile)
        elif use_profile is None:
            return self.__get_profile_storage()
        elif use_profile and use_profile in self.__browser_profile_list:
            use_profile_list.append(use_profile)
        elif type(use_profile) == list:
            use_profile_list.extend(self.__browser_profile_list)
        else:
            raise ValueError(
                "Invalid profile provided. Make sure you provided a list of profiles or a profile name."
            )

        for profile in use_profile_list:
            profile_storage_dict[profile] = self.__get_profile_storage(profile)

        return profile_storage_dict

    def create_new_session(self):
        return self.__get_profile_storage()

    def access_by_obj(self, wa_profile_list):
        verified_wa_profile_list = False
        for object_store_obj in wa_profile_list:
            if "WASecretBundle" in object_store_obj["key"]:
                verified_wa_profile_list = True
                break

        if not verified_wa_profile_list:
            raise ValueError(
                "This is not a valid profile list. Make sure you only pass one session to this method."
            )

        self.__start_visible_session(wait_for_login=False)
        self.__driver.execute_script(
            "window.waScript = {};"
            "window.waScript.insertDone = 0;"
            "window.waScript.jsonObj = undefined;"
            "window.waScript.setAllObjects = function (_jsonObj) {"
            "window.waScript.jsonObj = _jsonObj;"
            'window.waScript.dbName = "wawc";'
            'window.waScript.osName = "user";'
            "window.waScript.db;"
            "window.waScript.transaction;"
            "window.waScript.objectStore;"
            "window.waScript.clearRequest;"
            "window.waScript.addRequest;"
            "window.waScript.request = indexedDB.open(window.waScript.dbName);"
            "window.waScript.request.onsuccess = function(event) {"
            "window.waScript.db = event.target.result;"
            "window.waScript.transaction = window.waScript.db.transaction("
            'window.waScript.osName, "readwrite");'
            "window.waScript.objectStore = window.waScript.transaction.objectStore("
            "window.waScript.osName);"
            "window.waScript.clearRequest = window.waScript.objectStore.clear();"
            "window.waScript.clearRequest.onsuccess = function(clearEvent) {"
            "for (var i=0; i<window.waScript.jsonObj.length; i++) {"
            "window.waScript.addRequest = window.waScript.objectStore.add("
            "window.waScript.jsonObj[i]);"
            "window.waScript.addRequest.onsuccess = function(addEvent) {"
            "window.waScript.insertDone++;"
            "};"
            "}"
            "};"
            "};"
            "}"
        )
        self.__driver.execute_script(
            "window.waScript.setAllObjects(arguments[0]);", wa_profile_list
        )

        while not self.__driver.execute_script(
            "return (window.waScript.insertDone == window.waScript.jsonObj.length);"
        ):
            time.sleep(1)

        self.__driver.refresh()

        # while True:
        #     try:
        #         _ = self.__driver.window_handles
        #         time.sleep(1)
        #     except WebDriverException:
        #         break

    def access_by_file(self, profile_file):
        profile_file = os.path.normpath(profile_file)

        if os.path.isfile(profile_file):
            with open(profile_file, "r") as file:
                wa_profile_list = json.load(file)

            verified_wa_profile_list = False
            for object_store_obj in wa_profile_list:
                if "WASecretBundle" in object_store_obj["key"]:
                    verified_wa_profile_list = True
                    break
            if verified_wa_profile_list:
                self.access_by_obj(wa_profile_list)
            else:
                raise ValueError(
                    "There might be multiple profiles stored in this file."
                    " Make sure you only pass one WaSession file to this method."
                )
        else:
            raise FileNotFoundError(
                "Make sure you pass a valid WaSession file to this method."
            )

    def save_profile(self, wa_profile_list, file_path):
        file_path = os.path.normpath(file_path)

        verified_wa_profile_list = False
        for object_store_obj in wa_profile_list:
            if "key" in object_store_obj:
                if "WASecretBundle" in object_store_obj["key"]:
                    verified_wa_profile_list = True
                    break
        if verified_wa_profile_list:
            with open(file_path, "w") as file:
                json.dump(wa_profile_list, file, indent=4)
        else:
            saved_profiles = 0
            for profile_name in wa_profile_list.keys():
                profile_storage = wa_profile_list[profile_name]
                verified_wa_profile_list = False
                for object_store_obj in profile_storage:
                    if "key" in object_store_obj:
                        if "WASecretBundle" in object_store_obj["key"]:
                            verified_wa_profile_list = True
                            break
                if verified_wa_profile_list:
                    single_profile_name = (
                        os.path.basename(file_path) + "-" + profile_name
                    )
                    self.save_profile(
                        profile_storage,
                        os.path.join(os.path.dirname(file_path), single_profile_name),
                    )
                    saved_profiles += 1
            if saved_profiles > 0:
                pass
            else:
                raise ValueError(
                    "Could not find any profiles in the list. Make sure to specified file path is correct."
                )
