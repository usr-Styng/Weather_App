import os
import sys
import time
import requests
from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QUrl, QEvent
from PyQt5.QtMultimedia import QSoundEffect

class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Weather App")
        self.setFixedSize(700, 700)

        self.city_label = QLabel("Enter your city: ", self)
        self.city_input = QLineEdit(self)
        self.get_weather_button = QPushButton("Get weather", self)
        self.temperature_label = QLabel(self)
        self.emoji_label = QLabel(" ", self)
        self.description_label = QLabel(self)

        self.is_error = False

        # ---------------- SOUND SETUP ----------------
        CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
        sounds_dir = os.path.join(CURRENT_DIR, "ui-sounds")
        self.hover_file = os.path.join(sounds_dir, "hover.wav")
        self.click_file = os.path.join(sounds_dir, "click.wav")
        self.error_file = os.path.join(sounds_dir, "error.wav")

        self._hover_pool_size = 6
        self._hover_pool = []
        for _ in range(self._hover_pool_size):
            sfx = QSoundEffect()
            sfx.setSource(QUrl.fromLocalFile(self.hover_file))
            sfx.setLoopCount(1)
            sfx.setVolume(0.25)
            self._hover_pool.append(sfx)

        self._hover_pool_index = 0
        self._hover_min_interval = 0.100
        self._last_hover_time = 0.0

        self.click_sound = QSoundEffect()
        self.click_sound.setSource(QUrl.fromLocalFile(self.click_file))
        self.click_sound.setLoopCount(1)
        self.click_sound.setVolume(0.35)

        self.error_sound = QSoundEffect()
        self.error_sound.setSource(QUrl.fromLocalFile(self.error_file))
        self.error_sound.setLoopCount(1)
        self.error_sound.setVolume(0.45)

        self.get_weather_button.installEventFilter(self)

        self.initUI()

        self.get_weather_button.clicked.connect(self.get_weather)
        self.city_input.returnPressed.connect(self.get_weather)

    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.city_label)
        vbox.addWidget(self.city_input)
        vbox.addWidget(self.get_weather_button)
        vbox.addWidget(self.temperature_label)
        vbox.addWidget(self.emoji_label)
        vbox.addWidget(self.description_label)
        self.setLayout(vbox)

        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_input.setAlignment(Qt.AlignCenter)
        self.temperature_label.setAlignment(Qt.AlignCenter)
        self.emoji_label.setAlignment(Qt.AlignCenter)
        self.description_label.setAlignment(Qt.AlignCenter)

        self.city_label.setObjectName("city_label")
        self.city_input.setObjectName("city_input")
        self.get_weather_button.setObjectName("get_weather_button")
        self.temperature_label.setObjectName("temperature_label")
        self.emoji_label.setObjectName("emoji_label")
        self.description_label.setObjectName("description_label")

        self.setStyleSheet("""
            WeatherApp{
                background-color: black;
            }
            QLabel, QPushButton{
                font-family: jetbrains mono;
            }
            QLabel#city_label{
                font-size: 40px;
                font-style: itallic;
                color: white;
            }
            QLineEdit#city_input{
                font-size: 35px;
                font-family: jetbrains mono;
                color: black;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton#get_weather_button{
                font-size: 35px;
                font-weight: bold;
                color: black;
                background-color: white;
                border-radius: 15px;
            }
            QPushButton#get_weather_button:hover{
                background-color: black;
                color: white;
                border-color: white;
                border-width: 2.5px;
                border-style: solid;
            }
            QLabel#temperature_label{
                font-size: 75px;
                color: white;
            }
            QLabel#emoji_label{
                font-size: 75px;
                font-family: Segoe UI emoji;
            }
            QLabel#description_label{
                font-size: 50px;
                color: white;
            }
        """)

    # ---------------- WEATHER LOGIC ----------------
    def get_weather(self):
        city = self.city_input.text().strip()
        if not city:
            self.display_error("Please enter a city name.")
            self._play_error_sound()
            return

        api_key = "a50d826aac4ddf48b88d266342cf9df6"
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"

        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            data = response.json()

            cod = data.get("cod")
            if isinstance(cod, str) and cod.isdigit():
                cod = int(cod)

            if cod == 200:
                self.display_weather(data)
                self._play_click_sound()
            else:
                self.display_error(f"Unexpected API response: {cod}")
                self._play_error_sound()

        except requests.exceptions.HTTPError as http_error:
            status = getattr(http_error.response, "status_code", None)
            messages = {
                400: "Bad request — Check your input.",
                401: f"Unauthorized ({http_error}) — Invalid API key.",
                403: f"Forbidden ({http_error}) — Insufficient permissions.",
                404: f"City '{city}' not found.",
                500: "Internal Server Error.",
                502: "Bad Gateway.",
                503: "Service Unavailable.",
                504: "Gateway Timeout."
            }
            self.display_error(messages.get(status, f"Unknown HTTP error: {http_error}"))
            self._play_error_sound()

        except requests.exceptions.ConnectionError:
            self.display_error("Connection Error — Check your internet.")
            self._play_error_sound()

        except requests.exceptions.Timeout:
            self.display_error("Timeout — Server did not respond.")
            self._play_error_sound()

        except requests.exceptions.RequestException as req_error:
            self.display_error(f"Network error:\n{req_error}")
            self._play_error_sound()

    def display_error(self, message):
        self.is_error = True
        self.temperature_label.setStyleSheet("font-size: 15px; color: red;")
        self.temperature_label.setText(message)
        self.emoji_label.clear()
        self.description_label.clear()

    def display_weather(self, data):
        self.is_error = False
        self.temperature_label.setStyleSheet("font-size: 25px; color: white;")

        temp_k = data["main"]["temp"]
        feels_k = data["main"]["feels_like"]

        temp_c = temp_k - 273.15
        feels_c = feels_k - 273.15
        humidity = data["main"]["humidity"]
        high = data["main"]["temp_max"] - 273.15
        low = data["main"]["temp_min"] - 273.15
        desc = data["weather"][0]["description"]
        wid = data["weather"][0]["id"]

        self.temperature_label.setText(
            f"> Temperature: {temp_c:.0f}°C\n"
            f"> Feels like: {feels_c:.0f}°C\n"
            f"> Humidity: {humidity:.0f}% (rh)\n"
            f"> High: {high:.0f}°C\n"
            f"> Low: {low:.0f}°C"
        )

        self.emoji_label.setText(self.get_weather_emoji(wid))
        self.description_label.setText(f"overall weather:\n{desc}")


    def eventFilter(self, source, event):
        if source is self.get_weather_button and event.type() == QEvent.Enter:
            self._maybe_play_hover()
        return super().eventFilter(source, event)

    def _maybe_play_hover(self):
        now = time.monotonic()
        if now - self._last_hover_time < self._hover_min_interval:
            return
        self._last_hover_time = now

        sfx = self._hover_pool[self._hover_pool_index]
        self._hover_pool_index = (self._hover_pool_index + 1) % self._hover_pool_size
        sfx.play()


    def _play_click_sound(self):
        self.click_sound.play()

    def _play_error_sound(self):
        self.error_sound.play()


    @staticmethod
    def get_weather_emoji(weather_id):
        match weather_id:
            case _ if 200 <= weather_id <= 232: return "🌩️"
            case _ if 300 <= weather_id <= 321: return "🌦️"
            case _ if 500 <= weather_id <= 531: return "🌧️"
            case _ if 600 <= weather_id <= 622: return "❄️"
            case _ if 701 <= weather_id <= 741: return "🌫"
            case 762: return "🌋"
            case 771: return "💨"
            case 781: return "🌪️"
            case 800: return "☀️"
            case _ if 801 <= weather_id <= 804: return "☁️"
            case _: return " "


if __name__ == "__main__":
    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    weather_app.show()
    sys.exit(app.exec_())
