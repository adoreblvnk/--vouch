from wtforms import FileField, Form, StringField, SubmitField, validators


class VouchingDocumentsForm(Form):
    cbook_file = FileField("upload cashbook excel", validators=[
                           validators.DataRequired()])
    ref_id = StringField("", validators=[validators.DataRequired(), validators.length(
        min=1, max=50)], render_kw={"placeholder": "reference ID"})
    sheet_name = StringField("", validators=[validators.Optional(), validators.length(
        min=1, max=50)], render_kw={"placeholder": "(optional) sheet name"})
    start_col = StringField("", validators=[validators.Optional(), validators.length(
        min=1, max=3)], render_kw={"placeholder": "(optional) start column"})
    end_col = StringField("", validators=[validators.Optional(), validators.length(
        min=1, max=3)], render_kw={"placeholder": "(optional) end column"})
    invoice_zip = FileField("upload invoices zip.", validators=[
                            validators.DataRequired()])

