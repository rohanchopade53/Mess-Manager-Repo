def calculate_remaining_fee(student):
    return student["total_fees"] - student["received_amount"]

def format_mobile_number(mobile):

    mobile = str(mobile).strip()

    mobile = mobile.replace(" ", "")
    mobile = mobile.replace("-", "")

    if mobile.startswith("+91"):
        mobile = mobile[3:]

    if mobile.startswith("91") and len(mobile) == 12:
        return mobile

    if len(mobile) == 10:
        return "91" + mobile

    return mobile

def generate_reminder_message(student):

    remaining = calculate_remaining_fee(student)

    return (
        f"Hello {student['name']},\n\n"
        f"This is a reminder from Mess Manager.\n\n"
        f"Our records show your pending mess fee is ₹{remaining}.\n\n"
        f"Kindly pay it at your earliest convenience.\n\n"
        f"Thank you."
    )