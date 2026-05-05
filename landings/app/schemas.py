import re
from pydantic import BaseModel, field_validator

VALID_COUNTRY_CODES = {
    "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT",
    "AZ","BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW",
    "BV","BR","IO","BN","BG","BF","BI","CV","KH","CM","CA","KY","CF","TD","CL",
    "CN","CX","CC","CO","KM","CG","CD","CK","CR","CI","HR","CU","CW","CY","CZ",
    "DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ",
    "FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL","GD","GP",
    "GU","GT","GG","GN","GW","GY","HT","HM","VA","HN","HK","HU","IS","IN","ID",
    "IR","IQ","IE","IM","IL","IT","JM","JP","JE","JO","KZ","KE","KI","KP","KR",
    "KW","KG","LA","LV","LB","LS","LR","LY","LI","LT","LU","MO","MG","MW","MY",
    "MV","ML","MT","MH","MQ","MR","MU","YT","MX","FM","MD","MC","MN","ME","MS",
    "MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI","NE","NG","NU","NF","MK",
    "MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH","PN","PL","PT","PR",
    "QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","PM","VC","WS","SM","ST",
    "SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS","SS","ES",
    "LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK","TO",
    "TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","US","UM","UY","UZ","VU",
    "VE","VN","VG","VI","WF","EH","YE","ZM","ZW",
}

PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


class LeadIn(BaseModel):
    """POST /lead."""
    name: str
    phone: str
    country: str
    flow_id: str      # public_id потоку (наприклад "a2Ban4yOV8Av")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Олексій",
                "phone": "+380982342123",
                "country": "UA",
                "flow_id": "flow00000001",
            }
        }
    }

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name не може бути порожнім")
        return v

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("Невалідний формат телефону")
        return v

    @field_validator("country")
    @classmethod
    def country_valid(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in VALID_COUNTRY_CODES:
            raise ValueError(f"Невалідний код країни: {v}")
        return v


class LeadResponse(BaseModel):
    """Успішне прийняття ліда."""
    status: str = "queued"
    message: str = "Лід прийнято та поставлено в чергу"