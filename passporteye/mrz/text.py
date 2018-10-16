"""
PassportEye::MRZ: Machine-readable zone extraction and parsing.
MRZ textual representation parsing.

Author: Konstantin Tretyakov
License: MIT
"""

from collections import OrderedDict


class MRZ(object):
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
        """
        Parse a TD1/TD2/TD3/MRVA/MRVB MRZ from a single newline-separated string or a list of strings.

        :param mrz_lines: either a single string with newlines, or a list of 2 or 3 strings, representing the lines of an MRZ.
        :return: self
        """
        self._parse(mrz_lines)
        self.aux = {}


    @staticmethod
    def from_ocr(mrz_ocr_string):
        """Given a single string which is output from an OCR routine, cleans it up using MRZ.ocr_cleanup and creates a MRZ object"""
        return MRZ(MRZOCRCleaner.apply(mrz_ocr_string))

    def __repr__(self):
        if self.valid:
            return "MRZ({0}[valid], {1}, {2}, {3}, {4}, {5})".format(self.mrz_type, self.number, self.names, self.surname, self.sex, self.date_of_birth)
        elif self.valid_score > 0:
            return "MRZ({0}[{1}], {2}, {3}, {4}, {5}, {6})".format(self.mrz_type, self.valid_score, self.number, self.names, self.surname, self.sex, self.date_of_birth)
        else:
            return "MRZ(invalid)"

    @staticmethod
    def _guess_type(mrz_lines):
        """Guesses the type of the MRZ from given lines. Returns 'TD1', 'TD2', 'TD3', 'MRVA', 'MRVB' or None.
        The algorithm is basically just counting lines, looking at their length and checking whether the first character is a 'V'

        >>> MRZ._guess_type([]) is None
        True
        >>> MRZ._guess_type([1]) is None
        True
        >>> MRZ._guess_type([1,2]) is None  # No len() for numbers
        True
        >>> MRZ._guess_type(['a','b'])  # This way passes
        'TD2'
        >>> MRZ._guess_type(['*'*40, '*'*40])
        'TD3'
        >>> MRZ._guess_type([1,2,3])
        'TD1'
        >>> MRZ._guess_type(['V'*40, '*'*40])
        'MRVA'
        >>> MRZ._guess_type(['V'*36, '*'*36])
        'MRVB'
        """
        try:
            if len(mrz_lines) == 3:
                return 'TD1'
            elif len(mrz_lines) == 2 and len(mrz_lines[0]) < 40 and len(mrz_lines[1]) < 40:
                return 'MRVB' if mrz_lines[0][0].upper() == 'V' else 'TD2'
            elif len(mrz_lines) == 2:
                return 'MRVA' if mrz_lines[0][0].upper() == 'V' else 'TD3'
            else:
                return None
        except:
            return None

    def _parse(self, mrz_lines):
        from .mrz_parsers import supported_parsers

        self.mrz_type = MRZ._guess_type(mrz_lines)
        try:
            country = mrz_lines[0][2:5]  # Getting country COD (3 digits) on first line
            parser = supported_parsers[country](mrz_lines)
        except Exception:
            parser = supported_parsers['default'](mrz_lines)

        try:
            if self.mrz_type == 'TD1':
                self.valid, dictionary = parser.parse_td1()
            elif self.mrz_type == 'TD2':
                self.valid, dictionary = parser.parse_td2()
            elif self.mrz_type == 'TD3':
                self.valid, dictionary = parser.parse_td3()
            elif self.mrz_type == 'MRVA':
                self.valid, dictionary = parser.parse_mrv(length=44)
            elif self.mrz_type == 'MRVB':
                self.valid, dictionary = parser.parse_mrv(length=36)
            else:
                self.valid = False
                self.valid_score = 0

            # set all params of dictionary on class
            for key in dictionary:
                setattr(self, key, dictionary[key])

        except Exception:
            self.mrz_type = None
            self.valid = False
            self.valid_score = 0

    def to_dict(self):
        """Converts this object to an (ordered) dictionary of field-value pairs.

        >>> m = MRZ(['IDAUT10000999<6<<<<<<<<<<<<<<<', '7109094F1112315AUT<<<<<<<<<<<6', 'MUSTERFRAU<<ISOLDE<<<<<<<<<<<<']).to_dict()
        >>> assert m['type'] == 'ID' and m['country'] == 'AUT' and m['number'] == '10000999<'
        >>> assert m['valid_number'] and m['valid_date_of_birth'] and m['valid_expiration_date'] and not m['valid_composite']
        """

        result = OrderedDict()
        result['mrz_type'] = self.mrz_type
        result['valid_score'] = self.valid_score
        if self.mrz_type is not None:
            result['type'] = self.type
            result['country'] = self.country
            result['number'] = self.number
            result['date_of_birth'] = self.date_of_birth
            result['expiration_date'] = self.expiration_date
            result['nationality'] = self.nationality
            result['sex'] = self.sex
            result['names'] = self.names
            result['surname'] = self.surname
            if self.mrz_type == 'TD1':
                result['optional1'] = self.optional1
                result['optional2'] = self.optional2
            elif self.mrz_type in ['TD2', 'MRVA', 'MRVB']:
                result['optional1'] = self.optional1
            else:
                result['personal_number'] = self.personal_number
            result['check_number'] = self.check_number
            result['check_date_of_birth'] = self.check_date_of_birth
            result['check_expiration_date'] = self.check_expiration_date
            if self.mrz_type not in ['MRVA', 'MRVB']:
                result['check_composite'] = self.check_composite
            if self.mrz_type == 'TD3':
                result['check_personal_number'] = self.check_personal_number
            result['valid_number'] = self.valid_check_digits[0]
            result['valid_date_of_birth'] = self.valid_check_digits[1]
            result['valid_expiration_date'] = self.valid_check_digits[2]
            if self.mrz_type not in ['MRVA', 'MRVB']:
                result['valid_composite'] = self.valid_check_digits[3]
            if self.mrz_type == 'TD3':
                result['valid_personal_number'] = self.valid_check_digits[4]
            if 'method' in self.aux:
                result['method'] = self.aux['method']
        return result


class MRZOCRCleaner(object):
    """
    The __call__ method of this class implements the "cleaning" of an OCR-obtained string in preparation for MRZ parsing.
    This is a singleton class, so rather than creating an instance, simply use its `apply` static method.

    >>> MRZOCRCleaner.apply('\\nuseless lines\\n  P<POLKOWALSKA < KWIATKOWSKA<<JOANNA<<<<<<<<<<<extrachars \\n  AA0000000OP0L6OOzoB4Fi4iz3I4<<<<<<<<<<<<<<<4  \\n  asdf  ')
    ['P<POLKOWALSKA<KWIATKOWSKA<<JOANNA<<<<<<<<<<<extrachars', 'AA00000000POL6002084F1412314<<<<<<<<<<<<<<<4']

    """

    def __init__(self):
        # Specifications for which characters may be present at each position of each line of each document type.
        #   a  - alpha
        #   A  - alpha+<
        #   n  - numeric
        #   N  - numeric+<
        #   *  - alpha+num+<

        TD1 = ['a*' + 'A'*3 + '*'*9 + 'N' + '*'*15,
               'n'*7 + 'A' + 'n'*7 + 'A'*3 + '*'*11 + 'n',
               'A'*30]
        TD2 = ['a' + 'A'*35,
               '*'*9 + 'n' + 'A'*3 + 'n'*7 + 'A' + 'n'*7 + '*'*7 + 'n'*1]
        TD3 = ['a' + 'A'*43,
               '*'*9 + 'n' + 'A'*3 + 'n'*7 + 'A' + 'n'*7 + '*'*14 + 'n'*2 ]
        MRV = ['a' + 'A'*43,
               '*'*9 + 'n' + 'A'*3 + 'n'*7 + 'A' + 'n'*7 + '*'*16 ]
        self.FORMAT = {'TD1': TD1, 'TD2': TD2, 'TD3': TD3, 'MRVA': MRV, 'MRVB': MRV}

        # Fixers
        a = {'0': 'O', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '8': 'B' }
        n = {'B': '8', 'C': '0', 'D': '0', 'G': '6', 'I': '1', 'O': '0', 'Q': '0', 'S': '5', 'Z': '2'}
        self.FIXERS = {'a': a, 'A': a, 'n': n, 'N': n, '*': {}}

    def _split_lines(self, mrz_ocr_string):
        return [ln for ln in mrz_ocr_string.replace(' ', '').split('\n') if (len(ln) >= 20 or '<<' in ln)]

    def __call__(self, mrz_ocr_string):
        """
        Given a string, which is output from an OCR routine, splits it into lines and performs various ad-hoc cleaning on those.
        In particular:
            - Spaces are removed
            - Lines shorter than 30 non-space characters are removed
            - The type of the document is guessed based on the number of lines and their lengths,
              if it is not-none, OCR-fixup is performed on a character-by-character basis depending on
              what characters are allowed at particular positions.
        """
        lines = self._split_lines(mrz_ocr_string)
        tp = MRZ._guess_type(lines)
        if tp is not None:
            for i in range(len(lines)):
                lines[i] = self._fix_line(lines[i], tp, i)
        return lines

    def _fix_line(self, line, type, line_idx):
        ln = list(line)
        for j in range(len(ln)):
            ln[j] = self._fix_char(ln[j], type, line_idx, j)
        return ''.join(ln)

    def _fix_char(self, char, type, line_idx, char_idx):
        fmt = self.FORMAT[type][line_idx]
        if char_idx >= len(fmt):
            return char
        else:
            fixer = self.FIXERS[fmt[char_idx]]
            char = char.upper()
            return fixer.get(char, char)

    @staticmethod
    def apply(txt):
        if getattr(MRZOCRCleaner, '__instance__', None) is None:
            MRZOCRCleaner.__instance__ = MRZOCRCleaner()
        return MRZOCRCleaner.__instance__(txt)


class MRZCheckDigit(object):
    """
    The algorithm used to compute "check digits" within MRZ.
    Its __call__ method, given a string, returns either the single character check digit.
    Rather than creating an instance every time, use the static compute(txt) method (which makes use of a singleton instance).

    # Valid codes
    >>> assert MRZCheckDigit.compute('0') == '0'
    >>> assert MRZCheckDigit.compute('0000000000') == '0'
    >>> assert MRZCheckDigit.compute('00A0A<0A0<<0A0A0<0A') == '0'
    >>> assert MRZCheckDigit.compute('111111111') == '3'
    >>> assert MRZCheckDigit.compute('111<<<111111') == '3'
    >>> assert MRZCheckDigit.compute('BBB<<<1B1<<<BB1') == '3'
    >>> assert MRZCheckDigit.compute('1<<1<<1<<1') == '8'
    >>> assert MRZCheckDigit.compute('1<<1<<1<<1') == '8'
    >>> assert MRZCheckDigit.compute('BCDEFGHIJ') == MRZCheckDigit.compute('123456789')

    # Invalid codes
    >>> assert MRZCheckDigit.compute('') == ''
    >>> assert MRZCheckDigit.compute('0000 0') == ''
    >>> assert MRZCheckDigit.compute('0 0') == ''
    >>> assert MRZCheckDigit.compute('onlylowercase') == ''
    >>> assert MRZCheckDigit.compute('BBb<<<1B1<<<BB1') == ''

    """

    def __init__(self):
        self.CHECK_CODES = dict()
        for i in range(10):
            self.CHECK_CODES[str(i)] = i
        for i in range(ord('A'), ord('Z')+1):
            self.CHECK_CODES[chr(i)] = i - 55   # A --> 10, B --> 11, etc
        self.CHECK_CODES['<'] = 0
        self.CHECK_WEIGHTS = [7, 3, 1]

    def __call__(self, txt):
        if txt == '':
            return ''
        res = sum([self.CHECK_CODES.get(c, -1000)*self.CHECK_WEIGHTS[i % 3] for i, c in enumerate(txt)])
        if res < 0:
            return ''
        else:
            return str(res % 10)

    @staticmethod
    def compute(txt):
        if getattr(MRZCheckDigit, '__instance__', None) is None:
            MRZCheckDigit.__instance__ = MRZCheckDigit()
        return MRZCheckDigit.__instance__(txt)

