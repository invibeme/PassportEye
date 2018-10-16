from .text import MRZCheckDigit
from datetime import datetime

class MRZBaseParser:
    """
        A simple parser for a Type1 or Type3 Machine-readable zone strings from identification documents.
        See:
            - https://en.wikipedia.org/wiki/Machine-readable_passport
            - http://www.icao.int/publications/pages/publication.aspx?docnum=9303

        Usage:
            Represent the MRZ as a list of 2 or 3 lines, create an instance of this class,
            and read off the various fields filled by the parser.
            The first field you should check is .mrz_type.
            It is either None (no parsing done at all) or 'TD1', 'TD2', 'TD3', 'MRVA' or 'MRVB' depending on the type of the MRZ.
            The next one is 'valid'. If this is true, you may be pretty sure the parsing was successful and
            all the checksum digits passed the test as well. Sometimes the validity check may fail for some trivial reason
            (e.g. nonstandard document type character or one of the checksums wrong while others corect) -
            for this reason there is a field `valid_score`, which is an integer between 0 (nothing is valid) to 100
            (all checksums, line lengths and miscellaneous checks passed).

            Otherwise at least some of the checks failed, the meaning of which is up to you to interpret.
            When given invalid data, the algorithm attempts to do some trivial data clean-up: drop whitespaces from lines,
            and extend short lines with filler characters <, after which the fields are extracted from the lines as if
            they were valid.

            The parsing computes three validation indicators:
                valid_check_digits - a list of booleans indicating which of the "check digits" in the MRZ were valid.
                                    TD1/TD2 has four check digits, TD3 - five, MRVA/B - three.
                                    The separate booleans are also available as valid_number, valid_date_of_birth, valid_expiration_date, valid_composite
                                    and valid_personal_number (TD3 only).
                valid_line_lengths - a list of booleans, indicating which of the lines (3 in TD1, 2 in TD2/TD3) had the expected length.
                valid_misc         - a list of booleans, indicating various additional validity checks (unspecified, see code).
            The valid_score field counts the "validity score" according to the flags above and is an int between 0 and 100.
            When all validation passes, the valid field is set to True as well.
            However, you may attempt reading fields from a "not completely valid" MRZ as well sometimes.

            The reported fields are: type, country, number, date_of_birth, sex, expiration_date, nationality, names, surname
            TD1 MRZ also has fields optional1 and optional2. TD2 MRZ has optional1, TD3 MRZ has personal_number.
            MRVA and MRVB are the same as TD3 except personal_number and check_composite (which are not present)

            The field aux is a dictionary of additional data that may be associated with MRZ by OCR code,
            e.g. aux['roi'], aux['box'] or aux['text'] may be used to carry around the part of the image that was used
            to extract the information, aux['method'] to mark the method used, etc.

        # Valid ID card (TD1)
        >>> m = MRZ(['IDAUT10000999<6<<<<<<<<<<<<<<<', '7109094F1112315AUT<<<<<<<<<<<4', 'MUSTERFRAU<<ISOLDE<<<<<<<<<<<<'])
        >>> assert m.mrz_type == 'TD1' and m.valid and m.valid_score == 100
        >>> assert m.type == 'ID' and m.country == 'AUT' and m.number == '10000999<'
        >>> assert m.date_of_birth == '710909' and m.sex == 'F' and m.expiration_date == '111231' and m.nationality == 'AUT'
        >>> assert m.names == 'ISOLDE' and m.surname == 'MUSTERFRAU'
        >>> assert m.check_number == '6' and m.check_date_of_birth == '4' and m.check_expiration_date == '5' and m.check_composite == '4'
        >>> assert m.optional1 == '<<<<<<<<<<<<<<<' and m.optional2 == '<<<<<<<<<<<'

        # Valid TD2
        >>> m = MRZ(['I<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<', 'D231458907UTO7408122F1204159<<<<<<<6'])
        >>> assert m.mrz_type == 'TD2' and m.valid and m.valid_score == 100
        >>> assert m.type == 'I<' and m.country == 'UTO' and m.number == 'D23145890'
        >>> assert m.date_of_birth == '740812' and m.sex == 'F' and m.expiration_date == '120415' and m.nationality == 'UTO'
        >>> assert m.names == 'ANNA MARIA' and m.surname == 'ERIKSSON'
        >>> assert m.check_number == '7' and m.check_date_of_birth == '2' and m.check_expiration_date == '9' and m.check_composite == '6'

        # Valid Visa
        >>> m = MRZ(['VIUSATRAVELER<<HAPPYPERSON<<<<<<<<<<<<<<<<<<', '555123ABC6GBR6502056F04122361FLNDDDAM5803085'])
        >>> assert m.mrz_type == 'MRVA' and m.valid and m.valid_score == 100
        >>> assert m.type == 'VI' and m.country == 'USA' and m.number == '555123ABC'
        >>> assert m.date_of_birth == '650205' and m.sex == 'F' and m.expiration_date == '041223' and m.nationality == 'GBR'
        >>> assert m.names == 'HAPPYPERSON' and m.surname == 'TRAVELER'
        >>> assert m.check_number == '6' and m.check_date_of_birth == '6' and m.check_expiration_date == '6'

        # Valid passport (TD3)
        >>> m = MRZ(['P<POLKOWALSKA<KWIATKOWSKA<<JOANNA<<<<<<<<<<<', 'AA00000000POL6002084F1412314<<<<<<<<<<<<<<<4'])
        >>> assert m.mrz_type == 'TD3' and m.valid and m.valid_score == 100
        >>> assert m.type == 'P<' and m.country == 'POL' and m.number == 'AA0000000' and m.personal_number == '<<<<<<<<<<<<<<'
        >>> assert m.date_of_birth == '600208' and m.sex == 'F' and m.expiration_date == '141231' and m.nationality == 'POL'
        >>> assert m.names == 'JOANNA' and m.surname == 'KOWALSKA KWIATKOWSKA'
        >>> assert m.check_number == '0' and m.check_date_of_birth == '4' and m.check_expiration_date == '4' and m.check_personal_number == '<' and m.check_composite == '4'

        # Invalid examples
        >>> assert MRZ([]).mrz_type is None
        >>> assert MRZ([1,2,3,4]).mrz_type is None
        >>> assert MRZ([1,2,3]).mrz_type is None

        >>> m = MRZ(['IDAUT10000999<6<<<<<<<<<<<<<<<', '7109094F1112315AUT<<<<<<<<<<<6', 'MUSTERFRAU<<ISOLDE<<<<<<<<<<<<'])
        >>> assert m.mrz_type == 'TD1' and not m.valid and m.valid_score < 100
        >>> assert m.valid_check_digits == [True, True, True, False]
        >>> assert m.type == 'ID' and m.country == 'AUT' and m.number == '10000999<'

        # The utility from_ocr function will convert a single newline-separated string obtained as OCR output
        # into MRZ lines, doing some basic cleanup inbetween (removing empty lines and lines that are too short,
        # removing spaces, converting mismatched characters, etc), and then attempt the parsing.
        >>> m = MRZ.from_ocr('\\n\\n this line useless \\n IDAUT10000999<6  <<<<<<<<< <<<<<< \\n 7IO9O94FIi  iz3iSAUT<<<<<<<<<<<4 \\n MUSTERFRA  U<<ISOLDE<<<  <<<<<<<<<')
        >>> assert m.valid and m.names == 'ISOLDE' and m.surname == 'MUSTERFRAU'

        """

    def __init__(self, mrz_lines):
        self.mrz_lines = mrz_lines

    def parse_td1(self):
        a, b, c = self.mrz_lines
        len_a, len_b, len_c = len(a), len(b), len(c)
        if len(a) < 30:
            a = a + '<' * (30 - len(a))
        if len(b) < 30:
            b = b + '<' * (30 - len(b))
        if len(c) < 30:
            c = c + '<' * (30 - len(c))
        self.type = a[0:2]
        self.country = a[2:5]
        self.number = a[5:14]
        self.check_number = a[14]
        self.optional1 = a[15:30]
        self.date_of_birth = b[0:6]
        self.check_date_of_birth = b[6]
        self.sex = b[7]
        self.expiration_date = b[8:14]
        self.check_expiration_date = b[14]
        self.nationality = b[15:18]
        self.optional2 = b[18:29]
        self.check_composite = b[29]
        surname_names = c.split('<<', 1)
        if len(surname_names) < 2:
            surname_names += ['']
        self.surname, self.names = surname_names
        self.names = self.names.replace('<', ' ').strip()
        self.surname = self.surname.replace('<', ' ').strip()

        self.valid_check_digits = [MRZCheckDigit.compute(self.number) == self.check_number,
            MRZCheckDigit.compute(self.date_of_birth) == self.check_date_of_birth and self._check_date(self.date_of_birth),
            MRZCheckDigit.compute(self.expiration_date) == self.check_expiration_date and self._check_date(self.expiration_date),
            MRZCheckDigit.compute(a[5:30] + b[0:7] + b[8:15] + b[18:29]) == self.check_composite]
        self.valid_line_lengths = [len_a == 30, len_b == 30, len_c == 30]
        self.valid_misc = [a[0] in 'IAC']
        self.valid_score = 10 * sum(self.valid_check_digits) + sum(self.valid_line_lengths) + sum(self.valid_misc) + 1
        self.valid_score = 100 * self.valid_score // (40 + 3 + 1 + 1)
        self.valid_number, self.valid_date_of_birth, self.valid_expiration_date, self.valid_composite = self.valid_check_digits

        data = {
            'type': self.type,
            'country': self.country,
            'number': self.number,
            'check_number': self.check_number,
            'optional1': self.optional1,
            'date_of_birth': self.date_of_birth,
            'check_date_of_birth': self.check_date_of_birth,
            'sex': self.sex,
            'expiration_date': self.expiration_date,
            'check_expiration_date': self.check_expiration_date,
            'nationality': self.nationality,
            'optional2': self.optional2,
            'check_composite': self.check_composite,
            'surname': self.surname,
            'names': self.names,
            'valid_check_digits': self.valid_check_digits,
            'valid_line_lengths': self.valid_line_lengths,
            'valid_misc': self.valid_misc,
            'valid_score': self.valid_score,
            'valid_number': self.valid_number,
            'valid_date_of_birth': self.valid_date_of_birth,
            'valid_expiration_date': self.valid_expiration_date,
            'valid_composite': self.valid_composite
        }
        print("Estoy Eecutando MRZBaseParser")
        return self.valid_score == 100, data

    def parse_td2(self):
        a, b = self.mrz_lines
        len_a, len_b = len(a), len(b)
        if len(a) < 36:
            a = a + '<' * (36 - len(a))
        if len(b) < 36:
            b = b + '<' * (36 - len(b))
        self.type = a[0:2]
        self.country = a[2:5]
        surname_names = a[5:36].split('<<', 1)
        if len(surname_names) < 2:
            surname_names += ['']
        self.surname, self.names = surname_names
        self.names = self.names.replace('<', ' ').strip()
        self.surname = self.surname.replace('<', ' ').strip()
        self.number = b[0:9]
        self.check_number = b[9]
        self.nationality = b[10:13]
        self.date_of_birth = b[13:19]
        self.check_date_of_birth = b[19]
        self.sex = b[20]
        self.expiration_date = b[21:27]
        self.check_expiration_date = b[27]
        self.optional1 = b[28:35]
        self.check_composite = b[35]

        self.valid_check_digits = [MRZCheckDigit.compute(self.number) == self.check_number,
            MRZCheckDigit.compute(self.date_of_birth) == self.check_date_of_birth and self._check_date(self.date_of_birth),
            MRZCheckDigit.compute(self.expiration_date) == self.check_expiration_date and self._check_date(self.expiration_date),
            MRZCheckDigit.compute(b[0:10] + b[13:20] + b[21:35]) == self.check_composite]
        self.valid_line_lengths = [len_a == 36, len_b == 36]
        self.valid_misc = [a[0] in 'ACI']
        self.valid_score = 10 * sum(self.valid_check_digits) + sum(self.valid_line_lengths) + sum(self.valid_misc) + 1
        self.valid_score = 100 * self.valid_score // (40 + 2 + 1 + 1)
        self.valid_number, self.valid_date_of_birth, self.valid_expiration_date, self.valid_composite = self.valid_check_digits

        data = {
            'type': self.type,
            'country': self.country,
            'number': self.number,
            'check_number': self.check_number,
            'optional1': self.optional1,
            'date_of_birth': self.date_of_birth,
            'check_date_of_birth': self.check_date_of_birth,
            'sex': self.sex,
            'expiration_date': self.expiration_date,
            'check_expiration_date': self.check_expiration_date,
            'nationality': self.nationality,
            'check_composite': self.check_composite,
            'surname': self.surname,
            'names': self.names,
            'valid_check_digits': self.valid_check_digits,
            'valid_line_lengths': self.valid_line_lengths,
            'valid_misc': self.valid_misc,
            'valid_score': self.valid_score,
            'valid_number': self.valid_number,
            'valid_date_of_birth': self.valid_date_of_birth,
            'valid_expiration_date': self.valid_expiration_date,
            'valid_composite': self.valid_composite
        }
        return self.valid_score == 100, data

    def parse_td3(self):
        a, b = self.mrz_lines
        len_a, len_b = len(a), len(b)
        if len(a) < 44:
            a = a + '<' * (44 - len(a))
        if len(b) < 44:
            b = b + '<' * (44 - len(b))
        self.type = a[0:2]
        self.country = a[2:5]
        surname_names = a[5:44].split('<<', 1)
        if len(surname_names) < 2:
            surname_names += ['']
        self.surname, self.names = surname_names
        self.names = self.names.replace('<', ' ').strip()
        self.surname = self.surname.replace('<', ' ').strip()
        self.number = b[0:9]
        self.check_number = b[9]
        self.nationality = b[10:13]
        self.date_of_birth = b[13:19]
        self.check_date_of_birth = b[19]
        self.sex = b[20]
        self.expiration_date = b[21:27]
        self.check_expiration_date = b[27]
        self.personal_number = b[28:42]
        self.check_personal_number = b[42]
        self.check_composite = b[43]

        self.valid_check_digits = [MRZCheckDigit.compute(self.number) == self.check_number,
            MRZCheckDigit.compute(self.date_of_birth) == self.check_date_of_birth and self._check_date(self.date_of_birth),
            MRZCheckDigit.compute(self.expiration_date) == self.check_expiration_date and self._check_date(self.expiration_date),
            MRZCheckDigit.compute(b[0:10] + b[13:20] + b[21:43]) == self.check_composite,
                ((self.check_personal_number == '<' or self.check_personal_number == '0') and self.personal_number == '<<<<<<<<<<<<<<')  # PN is optional
                or MRZCheckDigit.compute(self.personal_number) == self.check_personal_number]
        self.valid_line_lengths = [len_a == 44, len_b == 44]
        self.valid_misc = [a[0] in 'P']
        self.valid_score = 10 * sum(self.valid_check_digits) + sum(self.valid_line_lengths) + sum(self.valid_misc) + 1
        self.valid_score = 100 * self.valid_score // (50 + 2 + 1 + 1)
        self.valid_number, self.valid_date_of_birth, self.valid_expiration_date, self.valid_personal_number, self.valid_composite = self.valid_check_digits

        data = {
            'type': self.type,
            'country': self.country,
            'names': self.names,
            'surname': self.surname,
            'number': self.number,
            'check_number': self.check_number,
            'nationality': self.nationality,
            'date_of_birth': self.date_of_birth,
            'check_date_of_birth': self.check_date_of_birth,
            'sex': self.sex,
            'expiration_date': self.expiration_date,
            'check_expiration_date': self.check_expiration_date,
            'personal_number': self.personal_number,
            'check_personal_number': self.check_personal_number,
            'check_composite': self.check_composite,
            'valid_check_digits': self.valid_check_digits,
            'valid_line_lengths': self.valid_line_lengths,
            'valid_misc': self.valid_misc,
            'valid_score': self.valid_score,
            'valid_number': self.valid_number,
            'valid_date_of_birth': self.valid_date_of_birth,
            'valid_expiration_date': self.valid_expiration_date,
            'valid_personal_number': self.valid_personal_number,
            'valid_composite': self.valid_composite
        }
        return self.valid_score == 100, data

    def parse_mrv(self, length):
        a, b = self.mrz_lines
        len_a, len_b = len(a), len(b)
        if len(a) < length:
            a = a + '<'*(44 - len(a))
        if len(b) < length:
            b = b + '<'*(44 - len(b))
        self.type = a[0:2]
        self.country = a[2:5]
        surname_names = a[5:length].split('<<', 1)
        if len(surname_names) < 2:
            surname_names += ['']
        self.surname, self.names = surname_names
        self.names = self.names.replace('<', ' ').strip()
        self.surname = self.surname.replace('<', ' ').strip()
        self.number = b[0:9]
        self.check_number = b[9]
        self.nationality = b[10:13]
        self.date_of_birth = b[13:19]
        self.check_date_of_birth = b[19]
        self.sex = b[20]
        self.expiration_date = b[21:27]
        self.check_expiration_date = b[27]
        self.optional1 = b[28:length]
        self.valid_check_digits = [MRZCheckDigit.compute(self.number) == self.check_number,
                             MRZCheckDigit.compute(self.date_of_birth) == self.check_date_of_birth,
                             MRZCheckDigit.compute(self.expiration_date) == self.check_expiration_date]
        self.valid_line_lengths = [len_a == length, len_b == length]
        self.valid_misc = [a[0]=='V']
        self.valid_score = 10*sum(self.valid_check_digits) + sum(self.valid_line_lengths) + sum(self.valid_misc) + 1
        self.valid_score = 100*self.valid_score//(30+2+1+1)
        self.valid_number, self.valid_date_of_birth, self.valid_expiration_date = self.valid_check_digits

        data = {
            'type': self.type,
            'country': self.country,
            'names': self.names,
            'surname': self.surname,
            'number': self.number,
            'check_number': self.check_number,
            'nationality': self.nationality,
            'date_of_birth': self.date_of_birth,
            'check_date_of_birth': self.check_date_of_birth,
            'sex': self.sex,
            'expiration_date': self.expiration_date,
            'check_expiration_date': self.check_expiration_date,
            'optional1': self.optional1,
            'valid_check_digits': self.valid_check_digits,
            'valid_line_lengths': self.valid_line_lengths,
            'valid_misc': self.valid_misc,
            'valid_score': self.valid_score,
            'valid_number': self.valid_number,
            'valid_date_of_birth': self.valid_date_of_birth,
            'valid_expiration_date': self.valid_expiration_date
        }
        return self.valid_score == 100, data

    @staticmethod
    def _check_date(ymd):
        try:
            datetime.strptime(ymd, '%y%m%d')
            return True
        except ValueError:
            return False


class MRZParserEsp(MRZBaseParser):
    """
    class to parser ID Cards of Spain
    """
    def parse_td1(self):
        a, b, c = self.mrz_lines
        len_a, len_b, len_c = len(a), len(b), len(c)
        if len(a) < 30:
            a = a + '<' * (30 - len(a))
        if len(b) < 30:
            b = b + '<' * (30 - len(b))
        if len(c) < 30:
            c = c + '<' * (30 - len(c))
        self.type = a[0:2]
        self.country = a[2:5]
        self.number = a[15:24]  # getting dni number of spain
        self.check_number = a[14]
        self.optional1 = a[15:30]
        self.date_of_birth = b[0:6]
        self.check_date_of_birth = b[6]
        self.sex = b[7]
        self.expiration_date = b[8:14]
        self.check_expiration_date = b[14]
        self.nationality = b[15:18]
        self.optional2 = b[18:29]
        self.check_composite = b[29]
        surname_names = c.split('<<', 1)
        if len(surname_names) < 2:
            surname_names += ['']
        self.surname, self.names = surname_names
        self.names = self.names.replace('<', ' ').strip()
        self.surname = self.surname.replace('<', ' ').strip()

        self.valid_check_digits = [MRZCheckDigit.compute(self.number) == self.check_number,
            MRZCheckDigit.compute(self.date_of_birth) == self.check_date_of_birth and self._check_date(self.date_of_birth),
            MRZCheckDigit.compute(self.expiration_date) == self.check_expiration_date and self._check_date(self.expiration_date),
            MRZCheckDigit.compute(a[5:30] + b[0:7] + b[8:15] + b[18:29]) == self.check_composite]
        self.valid_line_lengths = [len_a == 30, len_b == 30, len_c == 30]
        self.valid_misc = [a[0] in 'IAC']
        self.valid_score = 10 * sum(self.valid_check_digits) + sum(self.valid_line_lengths) + sum(self.valid_misc) + 1
        self.valid_score = 100 * self.valid_score // (40 + 3 + 1 + 1)
        self.valid_number, self.valid_date_of_birth, self.valid_expiration_date, self.valid_composite = self.valid_check_digits

        data = {
            'type': self.type,
            'country': self.country,
            'number': self.number,
            'check_number': self.check_number,
            'optional1': self.optional1,
            'date_of_birth': self.date_of_birth,
            'check_date_of_birth': self.check_date_of_birth,
            'sex': self.sex,
            'expiration_date': self.expiration_date,
            'check_expiration_date': self.check_expiration_date,
            'nationality': self.nationality,
            'optional2': self.optional2,
            'check_composite': self.check_composite,
            'surname': self.surname,
            'names': self.names,
            'valid_check_digits': self.valid_check_digits,
            'valid_line_lengths': self.valid_line_lengths,
            'valid_misc': self.valid_misc,
            'valid_score': self.valid_score,
            'valid_number': self.valid_number,
            'valid_date_of_birth': self.valid_date_of_birth,
            'valid_expiration_date': self.valid_expiration_date,
            'valid_composite': self.valid_composite
        }
        print("Estoy Eecutando MRZParserEsp")
        return self.valid_score == 100, data


# dict with diferents classes of parser
supported_parsers = {
    'ESP': MRZParserEsp,
    'default': MRZBaseParser
}
