import json
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
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 mb max size.
app.config["UPLOAD_FOLDER"] = "static/img/invoices"




@app.route("/")
def index():
    return render_template("index.html")


@app.route("/services/vouching", methods=["GET", "POST"])
def vouching():
    form = VouchingDocumentsForm(request.form)
    if request.method == "POST" and form.validate():
        invoices_dict = {}
        transactions_with_errors = {}
        cbook_file = form.cbook_file.data
        ref_id = form.ref_id.data
        sheet_name = form.sheet_name.data
        start_col = form.start_col.data
        end_col = form.end_col.data
        invoice_zip = form.invoice_zip.data
        try:
            unzip(invoice_zip, app.config["UPLOAD_FOLDER"])
        except zipfile.BadZipFile as e:
            flash("Invoices are not in ZIP format.", "danger")
            return render_template("vouching.html", form=form)
        except Exception as e:
            flash("Unknown error.", "danger")
            return render_template("vouching.html", form=form)
        for file in os.listdir(app.config["UPLOAD_FOLDER"]):
            file = file.lower()
            relative_path = f"{app.config['UPLOAD_FOLDER']}/{file}"
            try:
                if check_format(file) == "img":
                    img = cv2.imread(relative_path)
                elif check_format(file) == "doc":
                    img = pdftopil(relative_path)
                    img = merge_images(img)
                total_amount = invoice_total(img)
                # ref_id is the ID derived from file name.
                invoice_ref_id = Path(file).stem
                invoices_dict.update({invoice_ref_id: {"total_amount": total_amount}})
            except UnsupportedFileFormat as e:
                flash(
                    "File is unsupported. Check that invoice files are are documents & / images.", "danger")
                return render_template("vouching.html", form=form)
            except TotalKeywordNotFound as e:
                flash(f"{file} does not appear to have a total key.", "danger")
                return render_template("vouching.html", form=form)
            except TotalAmountNotFound as e:
                flash(f"{file} does not have a total amount.", "danger")
                return render_template("vouching.html", form=form)
            except Exception as e:
                flash("Unknown error.", "danger")
                return render_template("vouching.html", form=form)
        try:
            cashbook_dict = cbook_dict(
                cbook_file, ref_id, sheet_name, start_col, end_col)
        except ValueError:
            flash("Cashbook is not in excel format.", "danger")
            return render_template("vouching.html", form=form)
        except Exception as e:
            print("processing cashbook error", e)
            flash("Unknown error.", "danger")
            return render_template("vouching.html", form=form)
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
                flash("Error while processing invoices.", "danger")
                return render_template("vouching.html", form=form)
            except TotalKeywordNotFound as e:
                flash(
                    f"{cbook_file} does not appear to have a total keyword.", "danger")
                return render_template("vouching.html", form=form)
            except Exception as e:
                flash("Unknown error.", "danger")
                return render_template("vouching.html", form=form)
        try:
            with open("uploads/txn_errors.json", "w") as outfile:
                json.dump(transactions_with_errors, outfile, indent=4)
        except Exception as e:
            # TODO: handle error
            pass
        return redirect(url_for("vouching_results"))
    return render_template("vouching.html", form=form)


@app.route("/services/vouching_results")
def vouching_results():
    try:
        f = open("uploads/txn_errors.json", "r+")
        # TODO: delete json.
        data = json.load(f)
        return render_template("vouching_results.html", data=data)
    except Exception as e:
        # TODO: handle error
        return render_template("vouching_results.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")


if __name__ == "__main__":
    pass
