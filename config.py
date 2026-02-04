import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "usage_monitor.db"

IDLE_THRESHOLD_SEC = 180
POLL_INTERVAL_SEC = 1
SAVE_INTERVAL_SEC = 30

PRIVACY_MODE = "full"
BLACKLIST_WINDOWS = ["Пароль", "Password", "Личное", "Private", "Банк", "Bank"]

APP_CATEGORIES = {
    "work": {
        "keywords": [
            "code", "visual studio", "vscode", "pycharm", "intellij", "eclipse", "rider",
            "webstorm", "phpstorm", "goland", "clion", "datagrip", "android studio",
            "word", "excel", "powerpoint", "outlook", "teams", "onenote", "access",
            "slack", "notion", "jira", "confluence", "figma", "sketch", "adobe xd",
            "sublime", "notepad++", "atom", "brackets", "vim", "neovim", "emacs",
            "photoshop", "illustrator", "indesign", "premiere", "after effects",
            "blender", "unity", "unreal", "godot", "autocad", "solidworks",
            "postman", "insomnia", "dbeaver", "mysql workbench", "pgadmin",
            "git", "github desktop", "sourcetree", "gitkraken", "tortoisegit",
            "terminal", "iterm", "hyper", "warp", "powershell", "cmd",
            "docker", "kubernetes", "vagrant", "virtualbox", "vmware",
            "trello", "asana", "monday", "clickup", "basecamp", "linear",
            "miro", "lucidchart", "draw.io", "mindmeister",
            "1password", "lastpass", "bitwarden", "keepass",
            "calendar", "todoist", "ticktick", "things", "omnifocus"
        ],
        "name": "Рабочие"
    },
    "entertainment": {
        "keywords": [
            "steam", "epic games", "origin", "battle.net", "gog", "ubisoft", "ea app",
            "riot", "valorant", "league of legends", "dota", "counter-strike", "csgo", "cs2",
            "minecraft", "fortnite", "apex", "overwatch", "genshin", "roblox",
            "vlc", "spotify", "netflix", "youtube", "twitch", "kick", "rumble",
            "media player", "itunes", "winamp", "foobar", "musicbee", "aimp",
            "plex", "kodi", "jellyfin", "emby", "stremio",
            "disney+", "hbo", "amazon prime", "hulu", "crunchyroll", "funimation",
            "popcorn time", "stremio", "mpv", "potplayer", "kmplayer", "mpc-hc",
            "audacity", "ableton", "fl studio", "logic pro", "garageband", "reaper",
            "obs", "streamlabs", "xsplit", "nvidia broadcast",
            "retroarch", "dolphin", "yuzu", "ryujinx", "pcsx2", "rpcs3",
            "playnite", "launchbox", "gamepass", "xbox", "playstation", "geforce now"
        ],
        "name": "Развлечения"
    },
    "communication": {
        "keywords": [
            "telegram", "whatsapp", "viber", "discord", "skype", "signal", "element",
            "zoom", "google meet", "webex", "gotomeeting", "bluejeans",
            "messenger", "vk", "vkontakte", "facebook", "twitter", "x.com",
            "instagram", "tiktok", "snapchat", "pinterest", "reddit", "tumblr",
            "mail", "почта", "gmail", "outlook", "thunderbird", "mailspring", "spark",
            "slack", "teams", "mattermost", "rocket.chat", "zulip",
            "linkedin", "xing", "glassdoor",
            "clubhouse", "spaces", "twitter spaces",
            "wire", "wickr", "threema", "session",
            "icq", "aim", "yahoo messenger", "pidgin", "franz", "rambox", "station"
        ],
        "name": "Общение"
    },
    "browsers": {
        "keywords": [
            "chrome", "google chrome", "firefox", "mozilla", "opera", "edge", "safari",
            "yandex", "яндекс браузер", "brave", "vivaldi", "tor", "tor browser",
            "chromium", "ungoogled", "librewolf", "waterfox", "palemoon", "basilisk",
            "arc", "sidekick", "stack", "wavebox", "min", "qutebrowser",
            "internet explorer", "ie", "maxthon", "avant", "slim browser"
        ],
        "name": "Браузеры"
    },
    "system": {
        "keywords": [
            "explorer", "проводник", "cmd", "powershell", "terminal", "wt",
            "task manager", "диспетчер", "taskmgr", "process explorer", "process hacker",
            "settings", "параметры", "control panel", "панель управления",
            "regedit", "registry", "mmc", "services", "devmgmt", "diskmgmt",
            "notepad", "блокнот", "wordpad", "calculator", "калькулятор",
            "snipping tool", "ножницы", "paint", "photos", "фотографии",
            "file explorer", "total commander", "far manager", "double commander",
            "7-zip", "winrar", "winzip", "peazip", "bandizip",
            "ccleaner", "bleachbit", "glary", "wise care",
            "cpu-z", "gpu-z", "hwinfo", "speccy", "aida64", "hwmonitor",
            "msi afterburner", "rivatuner", "evga precision",
            "nvidia control", "amd software", "intel graphics",
            "windows update", "defender", "security", "firewall",
            "disk cleanup", "defragment", "chkdsk", "sfc"
        ],
        "name": "Системные"
    },
    "development": {
        "keywords": [
            "github", "gitlab", "bitbucket", "azure devops", "jenkins", "circleci",
            "node", "npm", "yarn", "pnpm", "bun", "deno",
            "python", "pip", "conda", "jupyter", "spyder", "idle",
            "java", "maven", "gradle", "ant", "tomcat",
            "dotnet", ".net", "nuget", "msbuild",
            "ruby", "rails", "gem", "bundler",
            "php", "composer", "laravel", "symfony",
            "rust", "cargo", "go", "golang",
            "kotlin", "scala", "clojure", "elixir", "erlang",
            "swift", "xcode", "cocoapods",
            "flutter", "dart", "react native", "expo",
            "webpack", "vite", "rollup", "parcel", "esbuild",
            "eslint", "prettier", "typescript", "babel"
        ],
        "name": "Разработка"
    },
    "productivity": {
        "keywords": [
            "obsidian", "roam", "logseq", "remnote", "mem", "craft",
            "evernote", "onenote", "bear", "apple notes", "simplenote",
            "google docs", "google sheets", "google slides", "google drive",
            "dropbox", "onedrive", "icloud", "mega", "pcloud", "sync",
            "notion", "coda", "airtable", "smartsheet",
            "pocket", "instapaper", "raindrop", "pinboard",
            "grammarly", "languagetool", "prowritingaid",
            "deepl", "google translate", "translate",
            "pdf", "acrobat", "foxit", "sumatra", "okular",
            "calibre", "kindle", "kobo", "moon reader"
        ],
        "name": "Продуктивность"
    }
}
