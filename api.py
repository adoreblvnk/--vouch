import os
import shutil
import zipfile
from pathlib import Path

import cv2
import numpy
import pandas as pd
import pdf2image
import pytesseract
from PIL import Image
from pytesseract.pytesseract import image_to_string

from exceptions import (TotalAmountNotFound, TotalKeywordNotFound,
                        UnsupportedFileFormat)

env = "dev"

if env == "dev":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    poppler_path = r"C:\Program Files\poppler-21.08.0\Library\bin"
else:
    pass


def unzip(zip_file, dir_2_extract):
    """
    description: unzips files.

    zip_file: file to unzip in ZIP format.
    dir_2_extract: directory to extract zip file in.
    """
    try:
        shutil.rmtree(dir_2_extract)
    except FileNotFoundError:
        pass
    with zipfile.ZipFile(zip_file) as z:
        z.extractall(dir_2_extract)


def check_format(file):
    """
    description: checks if file is in list of supported file formats. returns "img", "doc", or raises UnsupportedFileFormat error.

    file: file to check.
    """
    image, document = [".jpg", ".jpeg", ".png"], [".pdf"]
    if Path(str(file).lower()).suffix in image:
        return "img"
    elif Path(str(file).lower()).suffix in document:
        return "doc"
    else:
        raise UnsupportedFileFormat


def format_money(raw_doc):
    """"
    description: converts money into float-convertible strings. returns converted list of strings.

    raw_doc: raw document.
    """
    chars_to_remove = [",", "$"]
    for idx, word in enumerate(raw_doc):
        if any(c.isdigit() for c in word):
            for c in chars_to_remove:
                if c in word:
                    word = word.replace(c, "")
        else:
            continue
        raw_doc[idx] = word
    return raw_doc


def find_total(raw_doc):
    """
    description: extracts total amount of invoice from raw document in list format. returns total amount.

    raw_doc: raw document.
    """
    total, index_of_total = ["total", "subtotal"], 0
    for idx, word in enumerate(raw_doc):
        if word.lower() in total:
            index_of_total = idx + 1
    if index_of_total <= 1:
        raise TotalKeywordNotFound
    for amount in raw_doc[index_of_total:]:
        try:
            float(amount)
            return str(amount)
        except:
            continue
    raise TotalAmountNotFound


def invoice_total(img):
    """
    description: extracts total amount from invoice image. returns total amount.

    img: image.
    """
    # convert image to list of words.
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    raw_doc = str(image_to_string(img))
    raw_doc = " ".join([raw_doc]).split()
    raw_doc = format_money(raw_doc)
    total_amount = find_total(raw_doc)
    return total_amount


def pdftopil(pdf_path, dpi=200, format=".jpg", thread_count=1, use_cropbox=False, strict=False):
    """
    description: reads PDF & converts it into sequence of images. returns list of images in PIL format.

    pdf_path: sets path to PDF file.
    dpi: sets resolution of image.
    fmt: sets format of pdftoppm conversion (PpmImageFile, TIFF).
    thread_count: sets how many threads will be used for conversion.
    use_cropbox: uses crop box instead of media box given when converting.
    strict: catches pdftoppm syntax error with custom type PDFSyntaxError.
    """
    pil_images = pdf2image.convert_from_path(
        pdf_path, dpi=dpi, fmt=format, thread_count=thread_count,  use_cropbox=use_cropbox, strict=strict, poppler_path=poppler_path)
    return pil_images


def merge_images(pil_images):
    """
    description: merges list of images (in PIL format) into single image (cv2 format) vertically. returns single image in cv2 format.

    pil_images: list of images in PIL format.
    """
    width, height = zip(*(i.size for i in pil_images))
    min_width, total_height = min(width), sum(height)
    # create new image.
    new_img, new_pos = Image.new('RGB', (min_width, total_height)), 0
    for img in pil_images:
        new_img.paste(img, (0, new_pos))
        # position for the next image
        new_pos += img.size[1]
    new_img = cv2.cvtColor(numpy.array(new_img), cv2.COLOR_RGB2BGR)
    return new_img


def cbook_dict(cbook_file, ref_id, sheet_name=None, start_col=None, end_col=None):
    """
    description: converts contents of excel file into a dictionary. returns cashbook dictionary.

    cbook_file: excel file.
    red_id: column containing reference IDs of transactions.
    sheet_name: sheet to use.
    start_col: start column to extract data from.
    end_col: end column to extract data from.
    """
    cbook_dict = {}
    if sheet_name and start_col and end_col:
        cbook_df = pd.read_excel(
            cbook_file, sheet_name=sheet_name, usecols=f"{start_col}:{end_col}").dropna()
    elif sheet_name:
        cbook_df = pd.read_excel(
            cbook_file, sheet_name=sheet_name).dropna()
    elif start_col and end_col:
        cbook_df = pd.read_excel(
            cbook_file, usecols=f"{start_col}:{end_col}").dropna()
    else:
        cbook_df = pd.read_excel(cbook_file).dropna()
    for row in cbook_df.index:
        row_data = cbook_df.iloc[row]
        key = row_data[ref_id]
        cbook_dict[key] = {}
        del row_data[ref_id]
        for col in row_data.index:
            cbook_dict[key.lower()][col.lower()] = str(row_data[col])
    return cbook_dict


def transaction_amount_key(cashbook_dict):
    """
    description: searches for the transaction amount key. returns key.

    cashbook_dict: cashbook dictionary.
    """
    txn_key_list = ["cash", "amount", "credit", "payments", "payment"]
    for key in txn_key_list:
        if key in cashbook_dict[next(iter(cashbook_dict))].keys():
            return key
    raise TotalKeywordNotFound


def validate_transaction(cashbook_dict, invoices_dict, txn_to_check, txn_key):
    """
    description: validates whether the total amount of a transaction from the cashbook & the respective invoice corroborate. returns True / False & respective details.

    cashbook_dict: cashbook dictionary.
    invoices_dict: invoice dictionary.
    txn_to_check: transaction to check from cashbook dictionary.
    txn_key: transaction amount key, provided by transaction_amount_key().
    """
    if float(cashbook_dict[txn_to_check][txn_key]) == float(invoices_dict[txn_to_check]["total_amount"]):
        return True, cashbook_dict[txn_to_check][txn_key]
    elif float(cashbook_dict[txn_to_check][txn_key]) != float(invoices_dict[txn_to_check]["total_amount"]):
        return False, txn_to_check, cashbook_dict[txn_to_check][txn_key], invoices_dict[txn_to_check]["total_amount"]


if __name__ == "__main__":
    zip_file = "invoices.zip"
    dir_2_extract = "invoices"
    try:
        unzip(zip_file, dir_2_extract)
    except zipfile.BadZipFile as e:
        # TODO: fix custom error
        pass
    except Exception as e:
        # TODO: fix error
        pass
    invoices_dict = {}
    for file in os.listdir(dir_2_extract):
        file = file.lower()
        relative_path = f"{dir_2_extract}/{file}"
        try:
            if check_format(file) == "img":
                img = cv2.imread(relative_path)
            elif check_format(file) == "doc":
                img = pdftopil(relative_path)
                img = merge_images(img)
            total_amount = invoice_total(img)
            # ref_id is the ID derived from file name.
            ref_id = Path(file).stem
            invoices_dict.update({ref_id: {"total_amount": total_amount}})
        except UnsupportedFileFormat as e:
            # TODO: custom error
            pass
        except TotalKeywordNotFound as e:
            # TODO: custom error
            pass
        except TotalAmountNotFound as e:
            # TODO: custom error
            pass
        except Exception as e:
            # error w/ file
            pass

    cbook_file = "cashbook.xlsx"
    ref_id = "Reference_ID"
    sheet_name = "cashbook"
    start_col = ""
    end_col = ""
    try:
        cashbook_dict = cbook_dict(cbook_file, ref_id, sheet_name)
    except ValueError:
        # TODO: file not in excel format
        pass
    except Exception as e:
        # error
        pass

    transactions_with_errors = {}
    for txn_to_check in cashbook_dict:
        try:
            txn_key = transaction_amount_key(cashbook_dict)
            result = validate_transaction(
                cashbook_dict, invoices_dict, txn_to_check, txn_key)
            if result[0] == True:
                # TODO: no error.
                pass
            elif result[0] == False:
                transactions_with_errors[result[1]] = {
                    "cbook_amount": str(result[2]), "invoice_amount": str(result[3])}
        except AttributeError as e:
            # TODO: cashbook dictionary is corrupted, cannot unpack dictionary of txn
            pass
        except TotalKeywordNotFound as e:
            # TODO: custom error
            pass
        except Exception as e:
            pass
    print(transactions_with_errors)