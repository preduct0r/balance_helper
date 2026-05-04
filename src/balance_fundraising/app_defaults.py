from __future__ import annotations

DEFAULT_YANDEX_LLM_MODEL = "yandexgpt/latest"
DEFAULT_STORE_PATH = "data/local_store.json"
YANDEX_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YANDEX_SEARCH_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"

DEFAULT_DISCOVERY_QUERIES = [
    "прием заявок НКО платформа",
    "благотворительные фонды подать заявку",
    "партнерство НКО банк",
    "округление пожертвований НКО",
    "грант для НКО психическое здоровье",
]

DEFAULT_B2B_QUERIES = [
    "HR wellbeing партнерство НКО",
    "корпоративное благополучие психическое здоровье компания",
    "IT компания социальная ответственность психическое здоровье",
    "образовательная компания партнерство НКО психология",
    "медицинская компания CSR психическое здоровье",
    "креативная индустрия благотворительное партнерство НКО",
    "локальный бизнес регулярные пожертвования НКО",
]

DEFAULT_EVENT_QUERIES = [
    "НКО маркет подать заявку",
    "благотворительная ярмарка НКО участие",
    "маркет локальных брендов благотворительность",
    "городское мероприятие НКО участники",
    "инклюзивный фестиваль НКО маркет",
    "психопросвещение мероприятие партнеры",
]

DEFAULT_CURATED_SOURCES = [
    "https://dobro.mail.ru/funds/registration/",
    "https://corpcharity.help.yandex.ru/",
    "https://www.procharity.ru/",
]
