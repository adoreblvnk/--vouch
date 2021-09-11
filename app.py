import os
import zipfile
from pathlib import Path

import cv2
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for, flash
from wtforms import FileField, Form, StringField

from api import (cbook_dict, check_format, find_total, format_money,
                 invoice_total, merge_images, pdftopil, transaction_amount_key,
                 unzip, validate_transaction)
from exceptions import (TotalAmountNotFound, TotalKeywordNotFound,
                        UnsupportedFileFormat)
from forms import VouchingDocumentsForm

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024 # 50 mb max size.
app.config["UPLOAD_FOLDER"] = "static/img/invoices"


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/services/vouching', methods=["GET", "POST"])
def vouching():
    form = VouchingDocumentsForm(request.form)
    if request.method == "POST" and form.validate():
        cbook_file = form.cbook_file.data
        ref_id = form.ref_id.data
        sheet_name = form.sheet_name.data
        start_col = form.start_col.data
        end_col = form.end_col.data
        invoice_zip = form.invoice_zip.data

        
    return render_template("vouching.html", form=form)

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")


if __name__ == "__main__":
    zip_file = "drawingboard/invoices.zip"
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

    cbook_file = "drawingboard/cashbook.xlsx"
    ref_id = "Reference_ID"
    sheet_name = "cashbook"
    start_col = ""
    end_col = ""
    try:
        cashbook_dict = cbook_dict(cbook_file, ref_id, sheet_name)
    except ValueError:
        # TODO: file not in excel format
        print(e)
        pass
    except Exception as e:
        # error file does not exist
        print(e)
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
