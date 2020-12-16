from django import forms

from onlineshopping.models import Profile, Product

MAX_UPLOAD_SIZE = 2500000

class PostProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('product_name','description','product_photo','price','available_quantity')
        widgets = {
            'text': forms.TextInput(attrs={'id':'id_post_input_text'}),
        }
        labels = {
            'product_name': 'Name',
            'description': 'Description',
            'product_photo': 'Image',
            'price': 'Price',
            'available_quantity': 'Quantity'
        }
    def clean(self):
        cleaned_data = super().clean()
        picture = cleaned_data['product_photo']
        if cleaned_data['price'] < 0:
            raise forms.ValidationError('Price has to be positive.')
        if cleaned_data['available_quantity'] < 0:
            raise forms.ValidationError('Quantity has to be positive.')
        if picture:
            if not picture.content_type or not picture.content_type.startswith('image'):
                raise forms.ValidationError('File type is not image')
            if picture.size > MAX_UPLOAD_SIZE:
                raise forms.ValidationError('File too big (max size is {0} bytes)'.format(MAX_UPLOAD_SIZE))
        return cleaned_data


class EditAccount(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = (
            'user',
        )
        labels = {
            'first_name' : 'First Name',
            'last_name' : 'Last Name',
            'email' : 'E-mail',
            'phone' : 'Contact Number',
            'address' : 'Address',
            'city' : 'City',
            'state' : 'State',
            'zip_code' : 'Zip',
            'country' : 'Country',
        }
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
