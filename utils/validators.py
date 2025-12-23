# -*- coding: utf-8 -*-
"""
0;840B>@K 4;O ?@>25@:8 2E>4=KE 40==KE
"""

import re
from datetime import datetime
from typing import Union, Optional


class ValidationError(Exception):
    """A:;NG5=85 4;O >H81>: 20;840F88"""
    pass


def validate_phone(phone: str) -> bool:
    """
    @>25@O5B D>@<0B B5;5D>=0

    Args:
        phone: ><5@ B5;5D>=0

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not phone:
        raise ValidationError(""5;5D>= =5 <>65B 1KBL ?CABK<")

    # $>@<0B: +7 (XXX) XXX-XX-XX
    pattern = r'^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$'

    if not re.match(pattern, phone):
        raise ValidationError(
            "525@=K9 D>@<0B B5;5D>=0. 68405BAO: +7 (XXX) XXX-XX-XX"
        )

    return True


def validate_email(email: str) -> bool:
    """
    @>25@O5B D>@<0B email

    Args:
        email: Email 04@5A

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not email:
        return True  # Email =5>1O70B5;L=>5 ?>;5

    # 07>20O ?@>25@:0 email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        raise ValidationError("525@=K9 D>@<0B email")

    return True


def validate_amount(amount: Union[float, int, str], allow_zero: bool = True) -> bool:
    """
    @>25@O5B 45=56=CN AC<<C

    Args:
        amount: !C<<0
        allow_zero:  07@5H8BL =C;52>5 7=0G5=85

    Returns:
        True 5A;8 7=0G5=85 :>@@5:B=>5

    Raises:
        ValidationError: A;8 7=0G5=85 =5:>@@5:B=>5
    """
    try:
        amount_float = float(amount) if isinstance(amount, str) else amount
    except (ValueError, TypeError):
        raise ValidationError("!C<<0 4>;6=0 1KBL G8A;><")

    if amount_float < 0:
        raise ValidationError("!C<<0 =5 <>65B 1KBL >B@8F0B5;L=>9")

    if not allow_zero and amount_float == 0:
        raise ValidationError("!C<<0 =5 <>65B 1KBL =C;52>9")

    return True


def validate_date(date_str: str, allow_empty: bool = True) -> bool:
    """
    @>25@O5B D>@<0B 40BK

    Args:
        date_str: 0B0 2 D>@<0B5 DD.MM.YYYY
        allow_empty:  07@5H8BL ?CAB>5 7=0G5=85

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not date_str:
        if allow_empty:
            return True
        raise ValidationError("0B0 =5 <>65B 1KBL ?CAB>9")

    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        raise ValidationError("525@=K9 D>@<0B 40BK. 68405BAO: ..")


def validate_inn(inn: str) -> bool:
    """
    @>25@O5B  (10 8;8 12 F8D@)

    Args:
        inn: 

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not inn:
        return True  #  =5>1O70B5;L=>5 ?>;5

    if not re.match(r'^\d{10}$|^\d{12}$', inn):
        raise ValidationError(" 4>;65= A>45@60BL 10 8;8 12 F8D@")

    return True


def validate_ogrn(ogrn: str) -> bool:
    """
    @>25@O5B   (13 8;8 15 F8D@)

    Args:
        ogrn:  

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not ogrn:
        return True  #   =5>1O70B5;L=>5 ?>;5

    if not re.match(r'^\d{13}$|^\d{15}$', ogrn):
        raise ValidationError("  4>;65= A>45@60BL 13 8;8 15 F8D@")

    return True


def validate_passport(series: str, number: str) -> bool:
    """
    @>25@O5B A5@8N 8 =><5@ ?0A?>@B0

    Args:
        series: !5@8O ?0A?>@B0 (4 F8D@K)
        number: ><5@ ?0A?>@B0 (6 F8D@)

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not series and not number:
        return True  # 0A?>@B =5>1O70B5;L=>5 ?>;5

    if series and not re.match(r'^\d{4}$', series):
        raise ValidationError("!5@8O ?0A?>@B0 4>;6=0 A>45@60BL 4 F8D@K")

    if number and not re.match(r'^\d{6}$', number):
        raise ValidationError("><5@ ?0A?>@B0 4>;65= A>45@60BL 6 F8D@")

    return True


def validate_contract_number(contract_number: str) -> bool:
    """
    @>25@O5B =><5@ 4>3>2>@0

    Args:
        contract_number: ><5@ 4>3>2>@0

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not contract_number:
        raise ValidationError("><5@ 4>3>2>@0 =5 <>65B 1KBL ?CABK<")

    if len(contract_number) > 50:
        raise ValidationError("><5@ 4>3>2>@0 A;8H:>< 4;8==K9 (<0:A8<C< 50 A8<2>;>2)")

    return True


def validate_text_length(text: str, max_length: int, field_name: str = ">;5") -> bool:
    """
    @>25@O5B 4;8=C B5:AB>2>3> ?>;O

    Args:
        text: "5:AB
        max_length: 0:A8<0;L=0O 4;8=0
        field_name: 0720=85 ?>;O 4;O A>>1I5=8O >1 >H81:5

    Returns:
        True 5A;8 4;8=0 :>@@5:B=0O

    Raises:
        ValidationError: A;8 B5:AB A;8H:>< 4;8==K9
    """
    if text and len(text) > max_length:
        raise ValidationError(
            f"{field_name} A;8H:>< 4;8==>5 (<0:A8<C< {max_length} A8<2>;>2)"
        )

    return True


def sanitize_sql_identifier(identifier: str) -> str:
    """
    G8I05B 8<O 4;O 8A?>;L7>20=8O 2 SQL (70I8B0 >B 8=J5:F89)

    Args:
        identifier: <O ?>;O/B01;8FK

    Returns:
        G8I5==>5 8<O

    Raises:
        ValidationError: A;8 8<O A>45@68B =54>?CAB8<K5 A8<2>;K
    """
    #  07@5H5=K B>;L:> 1C:2K, F8D@K 8 ?>4GQ@:820=85
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValidationError(
            f"54>?CAB8<>5 8<O '{identifier}'. "
            " 07@5H5=K B>;L:> 1C:2K ;0B8=8FK, F8D@K 8 ?>4GQ@:820=85"
        )

    return identifier


def validate_area(area: Union[float, int, str]) -> bool:
    """
    @>25@O5B ?;>I04L

    Args:
        area: ;>I04L 2 :2.<

    Returns:
        True 5A;8 7=0G5=85 :>@@5:B=>5

    Raises:
        ValidationError: A;8 7=0G5=85 =5:>@@5:B=>5
    """
    try:
        area_float = float(area) if isinstance(area, str) else area
    except (ValueError, TypeError):
        raise ValidationError(";>I04L 4>;6=0 1KBL G8A;><")

    if area_float <= 0:
        raise ValidationError(";>I04L 4>;6=0 1KBL 1>;LH5 =C;O")

    if area_float > 100000:  # 0I8B0 >B A;CG09=KE >?5G0B>:
        raise ValidationError(";>I04L A;8H:>< 1>;LH0O (<0:A8<C< 100000 :2.<)")

    return True


def validate_login(login: str) -> bool:
    """
    @>25@O5B ;>38=

    Args:
        login: >38= ?>;L7>20B5;O

    Returns:
        True 5A;8 D>@<0B ?@028;L=K9

    Raises:
        ValidationError: A;8 D>@<0B =525@=K9
    """
    if not login:
        raise ValidationError(">38= =5 <>65B 1KBL ?CABK<")

    if len(login) < 3:
        raise ValidationError(">38= 4>;65= A>45@60BL <8=8<C< 3 A8<2>;0")

    if len(login) > 50:
        raise ValidationError(">38= A;8H:>< 4;8==K9 (<0:A8<C< 50 A8<2>;>2)")

    #  07@5H5=K 1C:2K, F8D@K, B>G:8, 45D8AK, ?>4GQ@:820=8O
    if not re.match(r'^[a-zA-Z0-9._-]+$', login):
        raise ValidationError(
            ">38= <>65B A>45@60BL B>;L:> 1C:2K, F8D@K 8 A8<2>;K: . _ -"
        )

    return True


def validate_password_strength(password: str) -> bool:
    """
    @>25@O5B =04Q6=>ABL ?0@>;O

    Args:
        password: 0@>;L

    Returns:
        True 5A;8 ?0@>;L =04Q6=K9

    Raises:
        ValidationError: A;8 ?0@>;L A;01K9
    """
    if not password:
        raise ValidationError("0@>;L =5 <>65B 1KBL ?CABK<")

    if len(password) < 6:
        raise ValidationError("0@>;L 4>;65= A>45@60BL <8=8<C< 6 A8<2>;>2")

    #  5:><5=40F88 4;O =04Q6=>AB8 (>?F8>=0;L=>)
    has_digit = bool(re.search(r'\d', password))
    has_letter = bool(re.search(r'[a-zA-Z0-O-/]', password))

    if not (has_digit and has_letter):
        # -B> ?@54C?@5645=85, => @07@5H05< B0:>9 ?0@>;L
        print("   5:><5=40F8O: 8A?>;L7C9B5 1C:2K 8 F8D@K 4;O 1>;LH59 =04Q6=>AB8")

    return True


# "5AB8@>20=85 20;840B>@>2
if __name__ == '__main__':
    print("=== "5AB <>4C;O validators ===\n")

    # "5AB B5;5D>=>2
    print("1. @>25@:0 B5;5D>=>2:")
    try:
        validate_phone("+7 (999) 123-45-67")
        print("   >@@5:B=K9 B5;5D>=")
    except ValidationError as e:
        print(f"   {e}")

    try:
        validate_phone("89991234567")
        print("   5:>@@5:B=K9 B5;5D>=")
    except ValidationError as e:
        print(f"   {e}")

    # "5AB email
    print("\n2. @>25@:0 email:")
    try:
        validate_email("user@example.com")
        print("   >@@5:B=K9 email")
    except ValidationError as e:
        print(f"   {e}")

    # "5AB AC<<
    print("\n3. @>25@:0 AC<<:")
    try:
        validate_amount(1000.50)
        print("   >@@5:B=0O AC<<0")
    except ValidationError as e:
        print(f"   {e}")

    try:
        validate_amount(-100)
        print("   B@8F0B5;L=0O AC<<0")
    except ValidationError as e:
        print(f"   {e}")

    # "5AB 40BK
    print("\n4. @>25@:0 40B:")
    try:
        validate_date("31.12.2024")
        print("   >@@5:B=0O 40B0")
    except ValidationError as e:
        print(f"   {e}")

    try:
        validate_date("2024-12-31")
        print("   5:>@@5:B=0O 40B0")
    except ValidationError as e:
        print(f"   {e}")

    print("\n=== A5 B5ABK 7025@H5=K ===")
