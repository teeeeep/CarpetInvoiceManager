from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, DateField
from wtforms.validators import DataRequired, Email, NumberRange
from wtforms.widgets import Input

class TouchNumberInput(Input):
    """Custom widget for touch-friendly number input"""
    input_type = 'number'
    
    def __call__(self, field, **kwargs):
        kwargs.setdefault('step', '0.01')
        kwargs.setdefault('min', '0')
        kwargs.setdefault('class', 'touch-input')
        return super(TouchNumberInput, self).__call__(field, **kwargs)

class RetailerForm(FlaskForm):
    """Form for retailer creation and editing"""
    name = StringField('Retailer Name', validators=[DataRequired()], 
                      render_kw={'class': 'form-input', 'placeholder': 'Enter retailer name'})
    email = StringField('Email Address', validators=[DataRequired(), Email()], 
                       render_kw={'class': 'form-input', 'placeholder': 'retailer@example.co.nz'})
    phone = StringField('Phone Number', validators=[DataRequired()], 
                       render_kw={'class': 'form-input', 'placeholder': '09-123-4567'})

class JobForm(FlaskForm):
    """Form for job creation and editing"""
    street_address = StringField('Street Address', validators=[DataRequired()], 
                                render_kw={'class': 'form-input', 'placeholder': '123 Main Street'})
    suburb = StringField('Suburb', validators=[DataRequired()], 
                        render_kw={'class': 'form-input', 'placeholder': 'Auckland Central'})
    town_city = StringField('Town/City', validators=[DataRequired()], 
                           render_kw={'class': 'form-input', 'placeholder': 'Auckland'})
    retailer_id = SelectField('Retailer', validators=[DataRequired()], coerce=int,
                             render_kw={'class': 'form-select'})
    homeowner_name = StringField('Homeowner Name', validators=[DataRequired()], 
                                render_kw={'class': 'form-input', 'placeholder': 'John Smith'})
    homeowner_phone = StringField('Homeowner Phone', validators=[DataRequired()], 
                                 render_kw={'class': 'form-input', 'placeholder': '021-123-4567'})
    date_completed = DateField('Date Completed', validators=[DataRequired()],
                              render_kw={'class': 'form-input'})

class InvoiceLineForm(FlaskForm):
    """Form for individual invoice line items"""
    description = TextAreaField('Description', validators=[DataRequired()], 
                               render_kw={'class': 'form-textarea', 'rows': '2', 
                                        'placeholder': 'Carpet installation - bedroom'})
    unit_price = FloatField('Unit Price (NZD)', validators=[DataRequired(), NumberRange(min=0)], 
                           widget=TouchNumberInput(),
                           render_kw={'class': 'form-input touch-input', 'placeholder': '0.00'})
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], 
                           render_kw={'class': 'form-input touch-input', 'placeholder': '1'})
