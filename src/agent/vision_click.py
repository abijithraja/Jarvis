import pyautogui
import pytesseract
import numpy as np


def find_and_click(text_to_find):
    screenshot = pyautogui.screenshot()
    img = np.array(screenshot)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    for i, word in enumerate(data["text"]):
        if text_to_find.lower() in word.lower():
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            pyautogui.click(x + w // 2, y + h // 2)
            return f"Clicked on {word}"

    return "Text not found on screen"
