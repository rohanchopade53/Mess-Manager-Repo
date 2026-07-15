import os



import pyperclip

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helpers import (
    generate_reminder_message,
    format_mobile_number
)





def open_whatsapp():

    options = Options()

    profile_path = r"C:\SeleniumProfile"

    os.makedirs(profile_path, exist_ok=True)

    options.add_argument(f"--user-data-dir={profile_path}")

    driver = webdriver.Chrome(
        service=Service(
            ChromeDriverManager().install()
        ),
        options=options
    )

    driver.get("https://web.whatsapp.com")

    print("✅ WhatsApp Web opened successfully!")

    return driver


def type_message(driver, message):

    message_box = WebDriverWait(driver, 20).until(

        EC.presence_of_element_located(

            (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')

        )

    )

    message_box.click()

    pyperclip.copy(message)

    message_box.send_keys(Keys.CONTROL, "v")

    print("✅ Message pasted successfully!")

    return message_box

def close_whatsapp(driver):

    driver.quit()

    return success, failed

def open_chat(driver, phone_number):

    url = f"https://web.whatsapp.com/send?phone={phone_number}"

    driver.get(url)

    WebDriverWait(driver, 20).until(

        EC.presence_of_element_located(

            (By.XPATH, '//div[@contenteditable="true"]')

        )

    )

    print(f"✅ Chat opened for {phone_number}")

def send_message(message_box):

    message_box.send_keys(Keys.ENTER)

    print("✅ Message sent successfully!")

def send_bulk_messages(students):

    driver = open_whatsapp()

    success = 0
    failed = 0

    for index, student in enumerate(students, start=1):

        try:

            phone = format_mobile_number(student["mobile"])

            message = generate_reminder_message(student)

            print(f"\n[{index}/{len(students)}] Sending to {student['name']} ({phone})")

            open_chat(driver, phone)

            message_box = type_message(driver, message)

            send_message(message_box)

            print("✅ Sent Successfully")

            success += 1

        except Exception as e:

            print(f"❌ Failed to send to {student['name']}")
            print(f"Reason: {e}")

            failed += 1

            continue

    print("\n" + "=" * 50)
    print("Bulk Messaging Finished")
    print(f"Successful : {success}")
    print(f"Failed     : {failed}")
    print("=" * 50)

    input("\nBulk messaging completed.\nPress Enter to close WhatsApp...")

    close_whatsapp(driver)

    return success, failed
if __name__ == "__main__":
    print("Run app.py to use WhatsApp reminders.")