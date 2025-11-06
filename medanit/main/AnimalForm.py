from django import forms
from .models import Animal

ANIMAL_SPECIES = [
    ('Собака', 'Собака'),
    ('Кошка', 'Кошка'),
    ('Кролик', 'Кролик'),
    # ... другие виды
    ('__other__', 'Прочее...'),
]

SPECIES_BREEDS = {
    'Собака': ['Лабрадор', 'Пудель', 'Бульдог', 'Двортерьер'],
    'Кошка': ['Сиамская', 'Персидская', 'Мейн-кун'],
    'Кролик': ['Ангорский', 'Рекс', 'Карликовый'],
    # ... добавьте другие виды и их породы
}

class AnimalForm(forms.ModelForm):
    species = forms.ChoiceField(
        choices=ANIMAL_SPECIES,
        widget=forms.Select(attrs={
            'class': 'form-select select2-species',
            'data-placeholder': 'Выберите вид'
        })
    )
    custom_species = forms.CharField(
        label="Свой вид",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mt-2 custom-input-hide',  # ВСЕГДА скрыто, JS покажет
            'placeholder': 'Укажите вид животного'
        })
    )

    breed = forms.ChoiceField(
        choices=[('', '---------')],  # Динамически в __init__
        widget=forms.Select(attrs={
            'class': 'form-select select2-breed',
            'data-placeholder': 'Выберите породу'
        }),
        required=False
    )
    custom_breed = forms.CharField(
        label="Собственная порода",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control mt-2 custom-input-hide',  # ВСЕГДА скрыто
            'placeholder': 'Укажите породу'
        })
    )

    class Meta:
        model = Animal
        fields = ['name', 'species', 'custom_species', 'breed', 'custom_breed', 'birthday', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кличка'}),
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data or None
        initial = self.initial or {}
        instance = getattr(self, 'instance', None)

        # Получаем выбранный вид
        species_val = (
            (data and data.get('species')) or
            initial.get('species') or
            (instance and instance.species)
        )

        breed_choices = [('', '---------')]
        if species_val in SPECIES_BREEDS:
            breed_choices += [(b, b) for b in SPECIES_BREEDS[species_val]]
            breed_choices += [('__other__', 'Прочее...')]
        elif species_val == '__other__':
            breed_choices += [('__other__', 'Прочее...')]
        else:
            breed_choices += [('__other__', 'Прочее...')]

        self.fields['breed'].choices = breed_choices

    def clean(self):
        cleaned_data = super().clean()
        species = cleaned_data.get('species')
        breed = cleaned_data.get('breed')

        # custom species
        if species == '__other__':
            custom_species = cleaned_data.get('custom_species')
            if custom_species:
                cleaned_data['species'] = custom_species.strip()
            else:
                self.add_error('custom_species', 'Заполните вид животного.')
        else:
            cleaned_data['custom_species'] = ''

        # custom breed
        if breed == '__other__':
            custom_breed = cleaned_data.get('custom_breed')
            if custom_breed:
                cleaned_data['breed'] = custom_breed.strip()
            else:
                self.add_error('custom_breed', 'Заполните породу животного.')
        else:
            cleaned_data['custom_breed'] = ''

        return cleaned_data