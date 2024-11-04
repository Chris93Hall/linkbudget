
import os

from . import convert

from fpdf import FPDF

def pad_string(string, length, side='left'):
    string = str(string)
    str_len = len(string)
    if str_len >= length:
        return string

    rem_length = length - str_len
    if side != 'left':
        return string + (' ' * rem_length) 
    return (' ' * rem_length) + string

def trunc_float(flt):
    flt = f'{flt:4f}'
    return float(flt)

def float_to_bounded_str(val, str_length=12):
    val_str = str(val)
    if len(val_str) <= str_length:
        return val_str

    val_str = f'{val:e}' # force scientific notarion
    if len(val_str) <= str_length:
        return val_str

    frac, exp = val_str.split('e')
    exp_length = len(exp)
    frac_length = str_length - exp_length - 1
    if frac[0] == '-':
        frac_length -= 1

    # if frac_length is 0 or -1, we can just use the whole number
    if frac_length in [0, -1]:
        return frac.split('.')[0] + 'e' + exp

    frac = frac[:frac_length]
    return frac + 'e' + exp
 

class PDFPublisher:
    def __init__(self, fpath):
        self.fpath = fpath
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.add_page()

    def add_header(self, text='Link Budget'):
        self.pdf.set_font("helvetica", "B", 15)
        # Moving cursor to the right:
        self.pdf.cell(40)
        # Printing title:
        self.pdf.cell(100, 10, text, border=1, align="C")
        # Performing a line break:
        self.pdf.ln(20)

    def publish_summary(self, data_list):
        self.add_header('LINK BUDGET SUMMARY')

        self.pdf.set_font("helvetica", 'B',  10)
        self.pdf.cell(30, 10, "Name")
        self.pdf.cell(35, 10, "Signal Power Out")
        self.pdf.cell(35, 10, "Noise Power Out")
        self.pdf.cell(35, 10, "Signal Gain (dB)")
        self.pdf.cell(35, 10, "Noise Gain (dB)")
        self.pdf.cell(40, 10, "SNR (dB)")

        self.pdf.set_font("helvetica", '',  10)
        for index, data, in enumerate(data_list):
            self.pdf.ln(12)
            name = data['name']
            sig_power_out = float_to_bounded_str(data['signal_power_out'])
            noise_power_out = float_to_bounded_str(data['noise_power_out'])
            noise_gain = float_to_bounded_str(convert.linear_to_db(data['noise_gain']))
            signal_gain = float_to_bounded_str(convert.linear_to_db(data['signal_gain']))
            snr = float_to_bounded_str(convert.linear_to_db(data['snr']))

            self.pdf.cell(35, 10, f'{index+1}. {name}')
            self.pdf.cell(30, 10, sig_power_out)
            self.pdf.cell(35, 10, noise_power_out)
            self.pdf.cell(35, 10, noise_gain)
            self.pdf.cell(35, 10, signal_gain)
            self.pdf.cell(40, 10, snr)

            description = data['description']
            if description:
                self.pdf.ln(7)
                self.pdf.cell(10)
                self.pdf.cell(100, 10, description)

        self.pdf.add_page()

    def publish_detailed(self, data_list):
        self.add_header('DETAILED LINK BUDGET REPORT')
        self.pdf.set_font("helvetica", '',  10)

        for index, data, in enumerate(data_list):
            self.pdf.cell(100, 10, f'{index + 1}. {data["name"]}')
            self.pdf.ln(10)
            for key in data.keys():
                pretty_key = key.replace('_', ' ')
                self.pdf.cell(10)
                self.pdf.cell(50, 10, pretty_key)
                self.pdf.cell(50, 10, str(data[key]))
                self.pdf.ln(7)
            self.pdf.ln(10)

    def publish(self, data_list):
        self.publish_summary(data_list)
        self.publish_detailed(data_list)
        self.pdf.output(self.fpath)


