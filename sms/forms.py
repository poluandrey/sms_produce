# sms/forms.py
import csv
import io
from django import forms
from django.core.exceptions import ValidationError
from openpyxl import load_workbook

from .models import Broadcast


def _only_digits(s: str) -> str:
    return ''.join(ch for ch in s if ch.isdigit())


class AddBroadcastForm(forms.ModelForm):
    # Доп. поле только для админки
    prefix_file = forms.FileField(
        required=False,
        label='Upload Prefix File',
        help_text='CSV/XLSX (один префикс в первой колонке, заголовок "prefix" допустим).'
    )

    class Meta:
        model = Broadcast
        fields = '__all__'

    # Сюда положим разобранные префиксы, чтобы потом взять их в admin.save_related
    parsed_prefixes: list[int] = []

    def clean_prefix_file(self):
        f = self.cleaned_data.get('prefix_file')
        if not f:
            return f
        name = f.name.lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx') or name.endswith('.xls') or name.endswith('.txt')):
            raise ValidationError('Поддерживаются файлы: .csv, .xlsx, .xls, .txt')

        return f

    def _parse_csv_or_txt(self, f) -> list[int]:
        # читаем в память с попыткой UTF-8, потом cp1251
        raw = f.read()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1251')
        sio = io.StringIO(text)

        # Попытаемся угадать разделитель
        try:
            sample = text.splitlines()[0]
            dialect = csv.Sniffer().sniff(sample, delimiters=',;|\t')
        except Exception:
            dialect = csv.excel

        reader = csv.reader(sio, dialect)
        out: list[int] = []
        for row in reader:
            if not row:
                continue
            value = str(row[0]).strip()
            if not value or value.lower() == 'prefix':
                continue
            value = _only_digits(value)
            if value:
                out.append(int(value))
        return out

    def _parse_xlsx(self, f) -> list[int]:
        wb = load_workbook(filename=f, read_only=True, data_only=True)
        ws = wb.active
        out: list[int] = []
        for row in ws.iter_rows(values_only=True):
            if not row:
                continue
            cell = row[0]
            if cell is None:
                continue
            value = str(cell).strip()
            if not value or value.lower() == 'prefix':
                continue
            value = _only_digits(value)
            if value:
                out.append(int(value))
        wb.close()
        return out

    def clean(self):
        cleaned = super().clean()
        f = cleaned.get('prefix_file')
        self.parsed_prefixes = []
        if f:
            name = f.name.lower()
            # NB: после чтения файл нельзя читать второй раз, поэтому парсим тут
            if name.endswith(('.csv', '.txt')):
                self.parsed_prefixes = self._parse_csv_or_txt(f)
            else:
                self.parsed_prefixes = self._parse_xlsx(f)

            # удалим дубликаты, сохранив порядок
            seen = set()
            unique = []
            for p in self.parsed_prefixes:
                if p not in seen:
                    seen.add(p)
                    unique.append(p)
            self.parsed_prefixes = unique

            if not self.parsed_prefixes:
                raise ValidationError({'prefix_file': 'Не найдено ни одного префикса.'})

        return cleaned
