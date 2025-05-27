import sys
import os
import json
import re
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, 
                           QComboBox, QTabWidget, QListWidget, QMessageBox, 
                           QSplitter, QFrame, QScrollArea, QGridLayout, QStackedWidget,
                           QDateTimeEdit, QCheckBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QLinearGradient, QBrush

# Import modules with proper error handling
try:
    import googlemaps
    GOOGLEMAPS_AVAILABLE = True
    # Your Google Maps API Key - REPLACE WITH YOUR ACTUAL KEY
    GOOGLE_MAPS_API_KEY = "your_google_maps_api_key_here"
except ImportError:
    GOOGLEMAPS_AVAILABLE = False
    GOOGLE_MAPS_API_KEY = None
    print("Warning: googlemaps not installed. Install with: pip install googlemaps")

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    # Your Gemini API Key - REPLACE WITH YOUR ACTUAL KEY
    GEMINI_API_KEY = "your_gemini_api_key_here"
except ImportError:
    GENAI_AVAILABLE = False
    GEMINI_API_KEY = None
    print("Warning: google-generativeai not installed. Install with: pip install google-generativeai")

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AUTH_AVAILABLE = True
    
    # Authentication settings
    SCOPES = ['openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile']

    TOKEN_FILE = 'token.json'
    
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("Warning: Google auth libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

class GlowButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("glowButton")
        self.base_style = ""
        
    def set_base_style(self, style):
        self.base_style = style
        self.setStyleSheet(style)
    
    def enterEvent(self, event):
        hover_style = self.base_style + """
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
                transform: translateY(-2px);
            }
        """
        self.setStyleSheet(hover_style)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        super().leaveEvent(event)

class AuthThread(QThread):
    auth_success = pyqtSignal(dict)
    auth_error = pyqtSignal(str)
    
    def run(self):
        if not GOOGLE_AUTH_AVAILABLE:
            self.auth_error.emit("Google authentication libraries not installed")
            return
        
        if not os.path.exists('credentials.json'):
            self.auth_error.emit("credentials.json file not found. Please download it from Google Cloud Console")
            return
        
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as refresh_error:
                        print(f"Token refresh failed: {refresh_error}")
                        # Delete invalid token and re-authenticate
                        if os.path.exists(TOKEN_FILE):
                            os.remove(TOKEN_FILE)
                        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                        creds = flow.run_local_server(port=0)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            
            # Get user info
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            
            # Save user info to file
            self.save_user_info(user_info)
            
            self.auth_success.emit(user_info)
            
        except Exception as e:
            self.auth_error.emit(f"Authentication failed: {str(e)}")
    
    def save_user_info(self, user_info):
        """Save user info to file"""
        try:
            with open('user_info.json', 'w') as f:
                json.dump(user_info, f, indent=2)
        except Exception as e:
            print(f"Error saving user info: {e}")

class GoogleMapsThread(QThread):
    directions_ready = pyqtSignal(dict)
    directions_error = pyqtSignal(str)
    
    def __init__(self, origin, destination, mode, departure_time):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.mode = mode
        self.departure_time = departure_time
    
    def run(self):
        if not GOOGLEMAPS_AVAILABLE:
            self.directions_error.emit("Google Maps library not installed")
            return
        
        if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == "YOUR_GOOGLE_MAPS_API_KEY_HERE":
            self.directions_error.emit("Google Maps API key not configured")
            return
        
        try:
            gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            
            # Get directions with error handling
            directions_result = gmaps.directions(
                self.origin,
                self.destination,
                mode=self.mode,
                departure_time=self.departure_time,
                traffic_model='best_guess' if self.mode == 'driving' else None,
                alternatives=False
            )
            
            if not directions_result:
                self.directions_error.emit("No route found between the specified locations")
                return
            
            route = directions_result[0]
            leg = route['legs'][0]
            
            # Format directions data with better error handling
            directions_data = {
                'origin': leg.get('start_address', self.origin),
                'destination': leg.get('end_address', self.destination),
                'mode': self.mode,
                'duration': leg.get('duration', {}).get('text', 'Unknown'),
                'distance': leg.get('distance', {}).get('text', 'Unknown'),
                'duration_in_traffic': leg.get('duration_in_traffic', {}).get('text', 'N/A'),
                'steps': []
            }
            
            # Process steps with HTML tag removal
            for i, step in enumerate(leg.get('steps', []), 1):
                instruction = self.clean_html_tags(step.get('html_instructions', ''))
                distance = step.get('distance', {}).get('text', 'Unknown')
                duration = step.get('duration', {}).get('text', 'Unknown')
                
                directions_data['steps'].append({
                    'step': i,
                    'instruction': instruction,
                    'distance': distance,
                    'duration': duration
                })
            
            self.directions_ready.emit(directions_data)
            
        except Exception as e:
            if "googlemaps.exceptions" in str(type(e)):
                self.directions_error.emit(f"Google Maps API error: {str(e)}")
            else:
                self.directions_error.emit(f"Error getting directions: {str(e)}")
    
    def clean_html_tags(self, text):
        """Remove HTML tags from text"""
        if not text:
            return ""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

class GeminiChatThread(QThread):
    response_received = pyqtSignal(str)
    
    def __init__(self, message, conversation_history, user_data=None, recent_journey=None):
        super().__init__()
        self.message = message
        self.conversation_history = conversation_history or []
        self.user_data = user_data or {}
        self.recent_journey = recent_journey
    
    def run(self):
        if not GENAI_AVAILABLE:
            self.response_received.emit("Gemini AI is not available. Please install google-generativeai library.")
            return
        
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            self.response_received.emit("Gemini API key not configured. Please set your API key.")
            return
        
        try:
            # Configure Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            # Build enhanced context with location and journey data
            context = self.build_enhanced_context()
            
            # Generate response
            response = model.generate_content(context)
            bot_reply = response.text.strip() if response.text else "I couldn't generate a response."
            
            self.response_received.emit(bot_reply)
            
        except Exception as e:
            error_msg = f"Error communicating with AI: {str(e)}"
            self.response_received.emit(error_msg)
    
    def build_enhanced_context(self):
        """Build enhanced context with location and journey data"""
        context_parts = []
        
        # Enhanced system prompt with travel expertise
        context_parts.append("""You are an expert travel assistant with access to real-time journey data and user history. 
        You have detailed knowledge of:
        - Travel routes, transportation options, and traffic patterns
        - Local attractions, restaurants, and accommodations
        - Weather conditions and seasonal travel tips
        - Budget planning and cost-effective travel options
        - Cultural insights and local customs
        - Safety tips and travel advisories
        
        Provide helpful, accurate, and personalized travel advice based on the user's location data and journey history.
        Be conversational, friendly, and specific in your recommendations. Use the journey data to give contextual advice.""")
        
        # Add recent journey data if available
        if self.recent_journey:
            journey_context = f"""
MOST RECENT JOURNEY:
- Origin: {self.recent_journey.get('origin', 'Unknown')}
- Destination: {self.recent_journey.get('destination', 'Unknown')}
- Travel Mode: {self.recent_journey.get('mode', 'Unknown')}
- Duration: {self.recent_journey.get('duration', 'Unknown')}
- Distance: {self.recent_journey.get('distance', 'Unknown')}
- Traffic Duration: {self.recent_journey.get('duration_in_traffic', 'N/A')}

Use this journey information to provide relevant travel advice, alternative routes, nearby attractions, 
dining options, or any other contextual recommendations."""
            context_parts.append(journey_context)
        
        # Add comprehensive journey history
        if self.user_data.get('journeys'):
            recent_journeys = self.user_data['journeys'][-10:]  # Last 10 journeys
            if recent_journeys:
                history_summary = "\nUSER'S RECENT JOURNEY HISTORY:\n"
                for idx, journey in enumerate(recent_journeys, 1):
                    data = journey.get('data', {})
                    timestamp = journey.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            time_str = timestamp[:16]
                    else:
                        time_str = "Unknown time"
                    
                    history_summary += f"{idx}. {time_str}: {data.get('origin', 'Unknown')} → {data.get('destination', 'Unknown')} "
                    history_summary += f"({data.get('mode', 'unknown')}, {data.get('duration', 'Unknown duration')})\n"
                
                history_summary += "\nUse this travel pattern to suggest personalized recommendations, "
                history_summary += "identify frequent routes, suggest optimizations, or recommend new destinations."
                context_parts.append(history_summary)
        
        # Add conversation context
        if self.conversation_history:
            context_parts.append("\nPREVIOUS CONVERSATION CONTEXT:")
            # Include last 6 messages for better context
            recent_messages = self.conversation_history[-6:]
            for message in recent_messages:
                context_parts.append(message)
        
        # Add current user message with clear marking
        context_parts.append(f"\nCURRENT USER QUESTION: {self.message}")
        context_parts.append("\nYour response should be helpful, specific, and based on the travel data provided above:")
        
        return "\n".join(context_parts)

class EnhancedTravelAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_info = None
        self.user_data_file = 'enhanced_travel_data.json'
        self.current_user_data = {}
        self.conversation_history = []
        self.most_recent_journey = None
        
        self.init_ui()
        self.show_login_screen()
    
    def init_ui(self):
        self.setWindowTitle("🌟 Smart Travel Assistant - Smart Maps + AI")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create stacked widget for different screens
        self.stacked_widget = QStackedWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(self.stacked_widget)
        
        # Create different screens
        self.create_login_screen()
        self.create_main_screen()
        
        # Apply styling
        self.apply_styling()
    
    def create_login_screen(self):
        login_widget = QWidget()
        layout = QVBoxLayout(login_widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # Add some top spacing
        layout.addStretch(1)
        
        # Title with glow effect
        title = QLabel("🌟 Smart Travel Assistant")
        title.setFont(QFont("Arial", 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                text-shadow: 0 0 20px rgba(102, 126, 234, 0.8);
                margin: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Subtitle with gradient text effect
        subtitle = QLabel("✨ Smart Maps + AI + Smart Journey Planning ✨")
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                margin: 10px;
                font-weight: 300;
            }
        """)
        layout.addWidget(subtitle)
        
        layout.addSpacing(50)
        
        # Enhanced login button
        self.login_btn = GlowButton("🚀 Login with Google")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.login_btn.clicked.connect(self.start_authentication)
        self.login_btn.setFixedSize(300, 60)
        layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)
        
        # Status label with styling
        self.login_status = QLabel("")
        self.login_status.setAlignment(Qt.AlignCenter)
        self.login_status.setStyleSheet("""
            QLabel {
                color: #4facfe;
                font-size: 14px;
                margin: 20px;
            }
        """)
        layout.addWidget(self.login_status)
        
        layout.addStretch(1)
        
        self.stacked_widget.addWidget(login_widget)
    
    def create_main_screen(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Enhanced header with gradient background
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.2));
                border-radius: 15px;
                padding: 20px;
                margin: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        self.welcome_label = QLabel("🎉 Welcome!")
        self.welcome_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.welcome_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
        """)
        header_layout.addWidget(self.welcome_label)
        
        header_layout.addStretch()
        
        logout_btn = GlowButton("🚪 Logout")
        logout_btn.clicked.connect(self.logout)
        logout_btn.setFixedSize(120, 40)
        header_layout.addWidget(logout_btn)
        
        layout.addWidget(header_frame)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # Google Maps Journey Tab
        self.maps_tab = self.create_maps_tab()
        self.tab_widget.addTab(self.maps_tab, "🗺️ Smart Maps")
        
        # Gemini AI Chat Tab
        self.ai_tab = self.create_ai_tab()
        self.tab_widget.addTab(self.ai_tab, "🤖 AI Chat")
        
        # Journey History Tab
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "📚 Journey History")
        
        layout.addWidget(self.tab_widget)
        
        self.stacked_widget.addWidget(main_widget)
    
    def create_maps_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Journey planning form with enhanced styling
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 20px;
                margin: 10px;
            }
        """)
        form_layout = QGridLayout(form_frame)
        form_layout.setSpacing(15)
        
        # Origin input
        origin_label = QLabel("📍 From:")
        origin_label.setFont(QFont("Arial", 12, QFont.Bold))
        origin_label.setWordWrap(True)
        form_layout.addWidget(origin_label, 0, 0)
        
        self.origin_input = QLineEdit()
        self.origin_input.setPlaceholderText("Enter starting location (e.g., Gelora Bung Karno Stadium, SCBD)")
        form_layout.addWidget(self.origin_input, 0, 1)
        
        # Destination input
        dest_label = QLabel("🎯 To:")
        dest_label.setFont(QFont("Arial", 12, QFont.Bold))
        dest_label.setWordWrap(True)
        form_layout.addWidget(dest_label, 1, 0)
        
        self.destination_input = QLineEdit()
        self.destination_input.setPlaceholderText("Enter destination (e.g., Monas, Kota Tua)")
        form_layout.addWidget(self.destination_input, 1, 1)
        
        # Travel mode
        mode_label = QLabel("🚗 Mode:")
        mode_label.setFont(QFont("Arial", 12, QFont.Bold))
        mode_label.setWordWrap(True)
        form_layout.addWidget(mode_label, 2, 0)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["driving", "walking", "bicycling", "transit"])
        form_layout.addWidget(self.mode_combo, 2, 1)
        
        # Departure time
        time_label = QLabel("⏰ Departure:")
        time_label.setFont(QFont("Arial", 12, QFont.Bold))
        time_label.setWordWrap(True)
        form_layout.addWidget(time_label, 3, 0)
        
        time_layout = QHBoxLayout()
        self.now_checkbox = QCheckBox("Leave now")
        self.now_checkbox.setChecked(True)
        self.now_checkbox.toggled.connect(self.toggle_departure_time)
        time_layout.addWidget(self.now_checkbox)
        
        self.departure_time = QDateTimeEdit(QDateTime.currentDateTime())
        self.departure_time.setEnabled(False)
        time_layout.addWidget(self.departure_time)
        
        form_layout.addLayout(time_layout, 3, 1)
        
        layout.addWidget(form_frame)
        
        # Get directions button
        self.get_directions_btn = GlowButton("🧭 Get Directions with Live Traffic")
        self.get_directions_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.get_directions_btn.clicked.connect(self.get_directions)
        self.get_directions_btn.setFixedHeight(50)
        layout.addWidget(self.get_directions_btn)
        
        # Directions results
        self.directions_display = QTextEdit()
        self.directions_display.setReadOnly(True)
        self.directions_display.setPlaceholderText("Your directions will appear here...")
        layout.addWidget(self.directions_display)
        
        return widget
    
    def create_ai_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # AI Chat header
        chat_header = QLabel("🤖 Chat with AI - Your Personal Travel Assistant")
        chat_header.setFont(QFont("Arial", 16, QFont.Bold))
        chat_header.setAlignment(Qt.AlignCenter)
        chat_header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.2));
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
            }
        """)
        layout.addWidget(chat_header)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Start chatting with AI about your travel plans...")
        layout.addWidget(self.chat_display)
        
        # Chat input area
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask me about travel tips, destinations, weather, or anything...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        input_layout.addWidget(self.chat_input)
        
        self.send_btn = GlowButton("Send")
        self.send_btn.clicked.connect(self.send_chat_message)
        self.send_btn.setFixedSize(80, 40)
        input_layout.addWidget(self.send_btn)
        
        layout.addWidget(input_frame)
        
        # Quick suggestion buttons
        suggestions_frame = QFrame()
        suggestions_layout = QHBoxLayout(suggestions_frame)
        
        quick_buttons = [
            ("🏖️ Beach destinations", "Suggest some beautiful beach destinations for a relaxing vacation"),
            ("🏔️ Mountain trips", "What are some great mountain destinations for hiking and adventure?"),
            ("🍕 Food travel", "Tell me about the best food destinations around the world"),
            ("💰 Budget tips", "Give me tips for budget-friendly travel")
        ]
        
        for text, prompt in quick_buttons:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, p=prompt: self.send_quick_message(p))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid #4a4a4a;
                    border-radius: 15px;
                    padding: 8px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(102, 126, 234, 0.3);
                }
            """)
            suggestions_layout.addWidget(btn)
        
        layout.addWidget(suggestions_frame)
        
        return widget
    
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # History header
        history_header = QLabel("📚 Your Journey History")
        history_header.setFont(QFont("Arial", 16, QFont.Bold))
        history_header.setAlignment(Qt.AlignCenter)
        history_header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.2));
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
            }
        """)
        layout.addWidget(history_header)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.on_history_item_clicked)
        layout.addWidget(self.history_list)
        
        # History controls
        controls_layout = QHBoxLayout()
        
        refresh_btn = GlowButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_history_display)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        
        clear_btn = GlowButton("🗑️ Clear History")
        clear_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_btn)
        
        layout.addLayout(controls_layout)
        
        return widget
    
    # Continuing from where the code was cut off...

    def apply_styling(self):
        self.setStyleSheet("""
            /* Main Window */
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
                color: #ffffff;
            }
            
            /* Stacked Widget */
            QStackedWidget {
                background: transparent;
            }
            
            /* Login Screen Styling */
            QWidget {
                background: transparent;
                color: #ffffff;
            }
            
            /* Labels */
            QLabel {
                color: #ffffff;
                font-weight: 500;
            }
            
            /* Tab Widget */
            QTabWidget::pane {
                border: 2px solid #4a4a4a;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(26, 26, 46, 0.9), stop:1 rgba(40, 44, 52, 0.9));
                margin-top: -2px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #3a3a5c, stop:1 #2a2a3e);
                color: #b0b0b0;
                padding: 12px 24px;
                margin: 2px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                color: #ffffff;
                border: 2px solid #667eea;
            }
            
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4a4a6a, stop:1 #3a3a5a);
                color: #ffffff;
            }
            
            /* Input Fields */
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.1), stop:1 rgba(255, 255, 255, 0.05));
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                color: #ffffff;
                selection-background-color: #667eea;
            }
            
            QLineEdit:focus {
                border: 2px solid #667eea;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(102, 126, 234, 0.1));
            }
            
            /* Text Edit */
            QTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 2px solid #4a4a4a;
                border-radius: 12px;
                padding: 15px;
                font-size: 14px;
                color: #ffffff;
                selection-background-color: #667eea;
            }
            
            QTextEdit:focus {
                border: 2px solid #667eea;
            }
            
            /* Combo Box */
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.1), stop:1 rgba(255, 255, 255, 0.05));
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                color: #ffffff;
                min-width: 100px;
            }
            
            QComboBox:focus {
                border: 2px solid #667eea;
            }
            
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 30px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border: 5px solid transparent;
                border-top: 8px solid #ffffff;
                margin-top: 2px;
            }
            
            QComboBox QAbstractItemView {
                background: #2a2a3e;
                border: 2px solid #667eea;
                border-radius: 8px;
                padding: 5px;
                color: #ffffff;
                selection-background-color: #667eea;
            }
            
            /* List Widget */
            QListWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.03));
                border: 2px solid #4a4a4a;
                border-radius: 12px;
                padding: 10px;
                font-size: 14px;
                color: #ffffff;
            }
            
            QListWidget::item {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid #4a4a4a;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
                color: #ffffff;
            }
            
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border: 2px solid #667eea;
                color: #ffffff;
            }
            
            QListWidget::item:hover {
                background: rgba(102, 126, 234, 0.3);
                border: 2px solid #667eea;
            }
            
            /* Date Time Edit */
            QDateTimeEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.1), stop:1 rgba(255, 255, 255, 0.05));
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                color: #ffffff;
            }
            
            QDateTimeEdit:focus {
                border: 2px solid #667eea;
            }
            
            /* Check Box */
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
                spacing: 10px;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #4a4a4a;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.1);
            }
            
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border: 2px solid #667eea;
            }
            
            /* Glow Button Base Style */
            #glowButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4facfe, stop:1 #00f2fe);
                border: none;
                border-radius: 12px;
                color: #ffffff;
                font-weight: bold;
                padding: 12px 24px;
                font-size: 14px;
            }
            
            #glowButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #3a8bdb, stop:1 #00d4db);
            }
            
            /* Login Button Special Style */
            #loginButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border: 2px solid transparent;
                border-radius: 15px;
                color: #ffffff;
                font-weight: bold;
                padding: 18px 36px;
                font-size: 16px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
            
            #loginButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #7c8cff, stop:1 #8a5fbf);
                border: 2px solid #667eea;
                transform: translateY(-2px);
            }
            
            /* Scrollbar */
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 6px;
                min-height: 30px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #7c8cff, stop:1 #8a5fbf);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)
        
        # Set button styles
        login_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border: 2px solid transparent;
                border-radius: 15px;
                color: #ffffff;
                font-weight: bold;
                padding: 18px 36px;
                font-size: 16px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
        """
        
        glow_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4facfe, stop:1 #00f2fe);
                border: none;
                border-radius: 12px;
                color: #ffffff;
                font-weight: bold;
                padding: 12px 24px;
                font-size: 14px;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #3a8bdb, stop:1 #00d4db);
            }
        """
        
        if hasattr(self, 'login_btn'):
            self.login_btn.set_base_style(login_button_style)
        
        # Apply glow button style to all glow buttons
        for button in self.findChildren(GlowButton):
            if button.objectName() != "loginButton":
                button.set_base_style(glow_button_style)
    
    def show_login_screen(self):
        """Show the login screen"""
        self.stacked_widget.setCurrentIndex(0)
    
    def show_main_screen(self):
        """Show the main application screen"""
        self.stacked_widget.setCurrentIndex(1)
        self.load_user_data()
        self.update_history_display()
    
    def start_authentication(self):
        """Start Google authentication process"""
        self.login_status.setText("🔄 Authenticating with Google...")
        self.login_btn.setEnabled(False)
        
        self.auth_thread = AuthThread()
        self.auth_thread.auth_success.connect(self.on_auth_success)
        self.auth_thread.auth_error.connect(self.on_auth_error)
        self.auth_thread.start()
    
    def on_auth_success(self, user_info):
        """Handle successful authentication"""
        self.user_info = user_info
        self.welcome_label.setText(f"🎉 Welcome, {user_info.get('name', 'User')}!")
        self.login_status.setText("✅ Authentication successful!")
        
        # Load user-specific data
        self.load_user_data()
        
        # Show main screen after a short delay
        QTimer.singleShot(1000, self.show_main_screen)
    
    def on_auth_error(self, error_message):
        """Handle authentication error"""
        self.login_status.setText(f"❌ {error_message}")
        self.login_btn.setEnabled(True)
        QMessageBox.warning(self, "Authentication Error", error_message)
    
    def logout(self):
        """Logout and return to login screen"""
        # Clear user data
        self.user_info = None
        self.current_user_data = {}
        self.conversation_history = []
        self.most_recent_journey = None
        
        # Clear displays
        self.chat_display.clear()
        self.directions_display.clear()
        self.history_list.clear()
        
        # Remove token file
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception as e:
                print(f"Error removing token file: {e}")
        
        # Reset login screen
        self.login_status.setText("")
        self.login_btn.setEnabled(True)
        
        # Show login screen
        self.show_login_screen()
    
    def load_user_data(self):
        """Load user-specific data from file"""
        if not self.user_info:
            return
        
        user_email = self.user_info.get('email', 'unknown')
        
        try:
            if os.path.exists(self.user_data_file):
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    all_user_data = json.load(f)
                    self.current_user_data = all_user_data.get(user_email, {
                        'journeys': [],
                        'conversations': [],
                        'preferences': {}
                    })
            else:
                self.current_user_data = {
                    'journeys': [],
                    'conversations': [],
                    'preferences': {}
                }
        except Exception as e:
            print(f"Error loading user data: {e}")
            self.current_user_data = {
                'journeys': [],
                'conversations': [],
                'preferences': {}
            }
    
    def save_user_data(self):
        """Save user-specific data to file"""
        if not self.user_info:
            return
        
        user_email = self.user_info.get('email', 'unknown')
        
        try:
            # Load existing data
            all_user_data = {}
            if os.path.exists(self.user_data_file):
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    all_user_data = json.load(f)
            
            # Update current user's data
            all_user_data[user_email] = self.current_user_data
            
            # Save back to file
            with open(self.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_user_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    def toggle_departure_time(self, checked):
        """Toggle departure time input"""
        self.departure_time.setEnabled(not checked)
    
    def get_directions(self):
        """Get directions from Google Maps"""
        origin = self.origin_input.text().strip()
        destination = self.destination_input.text().strip()
        
        if not origin or not destination:
            QMessageBox.warning(self, "Input Error", "Please enter both origin and destination")
            return
        
        mode = self.mode_combo.currentText()
        
        # Get departure time
        if self.now_checkbox.isChecked():
            departure_time = datetime.now()
        else:
            departure_time = self.departure_time.dateTime().toPyDateTime()
        
        # Disable button and show loading
        self.get_directions_btn.setEnabled(False)
        self.get_directions_btn.setText("🔄 Getting Directions...")
        self.directions_display.setText("🔄 Fetching directions with live traffic data...")
        
        # Start Google Maps thread
        self.maps_thread = GoogleMapsThread(origin, destination, mode, departure_time)
        self.maps_thread.directions_ready.connect(self.on_directions_ready)
        self.maps_thread.directions_error.connect(self.on_directions_error)
        self.maps_thread.start()
    
    def on_directions_ready(self, directions_data):
        """Handle directions results"""
        # Re-enable button
        self.get_directions_btn.setEnabled(True)
        self.get_directions_btn.setText("🧭 Get Directions with Live Traffic")
        
        # Format and display directions
        self.display_directions(directions_data)
        
        # Save journey to user data
        self.save_journey(directions_data)
        
        # Store most recent journey for AI context
        self.most_recent_journey = directions_data
        
        # Update history display
        self.update_history_display()
    
    def on_directions_error(self, error_message):
        """Handle directions error"""
        self.get_directions_btn.setEnabled(True)
        self.get_directions_btn.setText("🧭 Get Directions with Live Traffic")
        self.directions_display.setText(f"❌ Error: {error_message}")
        QMessageBox.warning(self, "Directions Error", error_message)
    
    def display_directions(self, directions_data):
        """Display formatted directions"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #ffffff; background: transparent;">
            <h2 style="color: #4facfe; margin-bottom: 20px;">🗺️ Your Journey Details</h2>
            
            <div style="background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <p><strong>📍 From:</strong> {directions_data['origin']}</p>
                <p><strong>🎯 To:</strong> {directions_data['destination']}</p>
                <p><strong>🚗 Mode:</strong> {directions_data['mode'].title()}</p>
                <p><strong>⏱️ Duration:</strong> {directions_data['duration']}</p>
                <p><strong>📏 Distance:</strong> {directions_data['distance']}</p>
                {'<p><strong>🚦 With Traffic:</strong> ' + directions_data['duration_in_traffic'] + '</p>' if directions_data['duration_in_traffic'] != 'N/A' else ''}
            </div>
            
            <h3 style="color: #00f2fe; margin-bottom: 15px;">📋 Step-by-Step Directions</h3>
        """
        
        for step in directions_data['steps']:
            html_content += f"""
            <div style="background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #4facfe;">
                <p><strong>Step {step['step']}:</strong> {step['instruction']}</p>
                <p style="color: #b0b0b0; font-size: 12px;">
                    📏 {step['distance']} • ⏱️ {step['duration']}
                </p>
            </div>
            """
        
        html_content += """
            <div style="background: rgba(102, 126, 234, 0.2); padding: 15px; border-radius: 10px; margin-top: 20px;">
                <p style="color: #4facfe; font-weight: bold;">💡 Pro Tip:</p>
                <p>Ask our AI assistant about this route for traffic tips, alternative routes, or nearby attractions!</p>
            </div>
        </div>
        """
        
        self.directions_display.setHtml(html_content)
    
    def save_journey(self, directions_data):
        """Save journey to user data"""
        journey_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': directions_data
        }
        
        # Add to current user data
        if 'journeys' not in self.current_user_data:
            self.current_user_data['journeys'] = []
        
        self.current_user_data['journeys'].append(journey_entry)
        
        # Keep only last 100 journeys to prevent file from getting too large
        if len(self.current_user_data['journeys']) > 100:
            self.current_user_data['journeys'] = self.current_user_data['journeys'][-100:]
        
        # Save to file
        self.save_user_data()
    
    def send_chat_message(self):
        """Send message to Gemini AI"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # Add user message to chat display
        self.add_chat_message("You", message, "#4facfe")
        
        # Clear input
        self.chat_input.clear()
        
        # Add to conversation history
        self.conversation_history.append(f"User: {message}")
        
        # Show loading message
        self.add_chat_message(" AI", "🤔 Thinking...", "#00f2fe")
        
        # Start Gemini chat thread
        self.chat_thread = GeminiChatThread(
            message, 
            self.conversation_history, 
            self.current_user_data,
            self.most_recent_journey
        )
        self.chat_thread.response_received.connect(self.on_chat_response)
        self.chat_thread.start()
    
    def send_quick_message(self, message):
        """Send quick message to AI"""
        self.chat_input.setText(message)
        self.send_chat_message()
    
    def on_chat_response(self, response):
        """Handle AI response"""
        # Remove loading message
        self.remove_last_chat_message()
        
        # Add AI response
        self.add_chat_message(" AI", response, "#00f2fe")
        
        # Add to conversation history
        self.conversation_history.append(f" AI: {response}")
        
        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        # Save conversation to user data
        self.save_conversation(response)
    
    def add_chat_message(self, sender, message, color):
        """Add message to chat display"""
        timestamp = datetime.now().strftime("%H:%M")
        
        # Create HTML formatted message
        html_message = f"""
        <div style="margin-bottom: 15px; padding: 12px; background: rgba(255, 255, 255, 0.05); border-radius: 10px; border-left: 4px solid {color};">
            <p style="margin: 0; color: {color}; font-weight: bold; font-size: 14px;">
                {sender} <span style="color: #888; font-weight: normal; font-size: 12px;">({timestamp})</span>
            </p>
            <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 14px; line-height: 1.4;">
                {message.replace('/n', '<br>')}
            </p>
        </div>"""
        
        # Append to chat display
        current_html = self.chat_display.toHtml()
        if "<body" in current_html:
            # Insert before closing body tag
            updated_html = current_html.replace("</body>", html_message + "</body>")
        else:
            # Simple append
            updated_html = current_html + html_message
        
        self.chat_display.setHtml(updated_html)
        
        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def remove_last_chat_message(self):
        """Remove the last message from chat display"""
        html = self.chat_display.toHtml()
        # Find and remove the last message div
        last_div_start = html.rfind('<div style="margin-bottom: 15px;')
        if last_div_start != -1:
            # Find the closing div
            div_count = 1
            search_pos = last_div_start + 20
            while search_pos < len(html) and div_count > 0:
                if html[search_pos:search_pos+4] == '<div':
                    div_count += 1
                elif html[search_pos:search_pos+6] == '</div>':
                    div_count -= 1
                search_pos += 1
            
            if div_count == 0:
                updated_html = html[:last_div_start] + html[search_pos:]
                self.chat_display.setHtml(updated_html)
    
    def save_conversation(self, ai_response):
        """Save conversation to user data"""
        if 'conversations' not in self.current_user_data:
            self.current_user_data['conversations'] = []
        
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'ai_response': ai_response,
            'context_journey': self.most_recent_journey
        }
        
        self.current_user_data['conversations'].append(conversation_entry)
        
        # Keep only last 50 conversations
        if len(self.current_user_data['conversations']) > 50:
            self.current_user_data['conversations'] = self.current_user_data['conversations'][-50:]
        
        self.save_user_data()
    
    def update_history_display(self):
        """Update the journey history display"""
        self.history_list.clear()
        
        if not self.current_user_data.get('journeys'):
            item = QListWidgetItem("No journey history available yet.\nPlan your first journey using the Smart Maps tab!")
            item.setFlags(Qt.NoItemFlags)  # Make it non-selectable
            self.history_list.addItem(item)
            return
        
        # Sort journeys by timestamp (most recent first)
        journeys = sorted(
            self.current_user_data['journeys'], 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        for journey in journeys:
            data = journey.get('data', {})
            timestamp = journey.get('timestamp', '')
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = timestamp[:16] if timestamp else "Unknown time"
            
            # Create list item
            origin = data.get('origin', 'Unknown')
            destination = data.get('destination', 'Unknown')
            mode = data.get('mode', 'unknown').title()
            duration = data.get('duration', 'Unknown')
            distance = data.get('distance', 'Unknown')
            
            # Truncate long addresses
            if len(origin) > 40:
                origin = origin[:37] + "..."
            if len(destination) > 40:
                destination = destination[:37] + "..."
            
            item_text = f"""🕒 {time_str}
📍 From: {origin}
🎯 To: {destination}
🚗 Mode: {mode} • ⏱️ {duration} • 📏 {distance}"""
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, journey)  # Store full journey data
            self.history_list.addItem(item)
    
    # Complete the incomplete method and add missing methods

    def on_history_item_clicked(self, item):
        """Handle clicking on history item"""
        journey_data = item.data(Qt.UserRole)
        if not journey_data:
            return
        
        data = journey_data.get('data', {})
        
        # Show detailed journey info
        self.show_journey_details(data)
        
        # Switch to maps tab and populate fields
        self.tab_widget.setCurrentIndex(0)  # Maps tab
        
        # Extract city/location names from full addresses
        origin = data.get('origin', '')
        destination = data.get('destination', '')
        
        self.origin_input.setText(origin)
        self.destination_input.setText(destination)
        
        # Set mode
        mode = data.get('mode', 'driving')
        index = self.mode_combo.findText(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
    
    def show_journey_details(self, data):
        """Show detailed journey information in a message box"""
        details = f"""
🗺️ Journey Details

📍 From: {data.get('origin', 'Unknown')}
🎯 To: {data.get('destination', 'Unknown')}
🚗 Mode: {data.get('mode', 'unknown').title()}
⏱️ Duration: {data.get('duration', 'Unknown')}
📏 Distance: {data.get('distance', 'Unknown')}
🚦 With Traffic: {data.get('duration_in_traffic', 'N/A')}

Steps: {len(data.get('steps', []))} navigation steps
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Journey Details")
        msg_box.setText(details)
        msg_box.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #2a2a3e, stop:1 #3a3a5c);
                color: #ffffff;
            }
            QMessageBox QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4facfe, stop:1 #00f2fe);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        msg_box.exec_()
    
    def clear_history(self):
        """Clear all journey history"""
        reply = QMessageBox.question(
            self, 
            "Clear History", 
            "Are you sure you want to clear all journey history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.current_user_data['journeys'] = []
            self.current_user_data['conversations'] = []
            self.save_user_data()
            self.update_history_display()
            self.chat_display.clear()
            self.conversation_history = []
            self.most_recent_journey = None
            
            QMessageBox.information(self, "History Cleared", "All history has been cleared successfully!")
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Save user data before closing
        if self.user_info:
            self.save_user_data()
        
        # Stop any running threads
        if hasattr(self, 'auth_thread') and self.auth_thread.isRunning():
            self.auth_thread.quit()
            self.auth_thread.wait()
        
        if hasattr(self, 'maps_thread') and self.maps_thread.isRunning():
            self.maps_thread.quit()
            self.maps_thread.wait()
        
        if hasattr(self, 'chat_thread') and self.chat_thread.isRunning():
            self.chat_thread.quit()
            self.chat_thread.wait()
        
        event.accept()


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Smart Travel Assistant")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Travel Assistant Co.")
    
    # Check for required dependencies
    missing_deps = []
    
    if not GOOGLEMAPS_AVAILABLE:
        missing_deps.append("googlemaps")
    
    if not GENAI_AVAILABLE:
        missing_deps.append("google-generativeai")
    
    if not GOOGLE_AUTH_AVAILABLE:
        missing_deps.append("google-auth libraries")
    
    if missing_deps:
        print("⚠️  Warning: Some features may not work properly.")
        print("Missing dependencies:", ", ".join(missing_deps))
        print("\nTo install missing dependencies:")
        if "googlemaps" in missing_deps:
            print("  pip install googlemaps")
        if "google-generativeai" in missing_deps:
            print("  pip install google-generativeai")
        if "google-auth libraries" in missing_deps:
            print("  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        print()
    
    # Check API keys
    api_warnings = []
    
    if GOOGLE_MAPS_API_KEY == "AIzaSyAjr22BdTMY0YnaWf0FE9IvDgU7sRbXX4U":
        api_warnings.append("Google Maps API key needs to be replaced")
    
    if GEMINI_API_KEY == "AIzaSyBydO1j5gFvt_rxBsEqObAfQ5BlvENtW0o":
        api_warnings.append("AI API key needs to be replaced")
    
    if api_warnings:
        print("🔑 API Key Warning:")
        for warning in api_warnings:
            print(f"  - {warning}")
        print("Please replace the placeholder API keys with your actual keys.")
        print()
    
    # Create and show main window
    window = EnhancedTravelAssistant()
    window.show()
    
    # Start the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
