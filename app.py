import os
import sys
import typing
from PyQt6 import QtCore, QtGui
# The library to convert opneAI response, which is Markdown, to HTML
import markdown
from datetime import datetime
# The library to read configuration file 
from configparser import ConfigParser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider,
    QTabWidget, QTextEdit, QTextBrowser, QMenu, QMenuBar, QSplitter,
    QToolButton, QStatusBar,
    QHBoxLayout, QVBoxLayout, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import QObject, Qt, QSize, pyqtSignal, QEvent, QThread, QMutex, QMutexLocker
from PyQt6.QtGui import QIcon, QTextCursor
from chatgpt import ChatGPT
from db import ChatGPTDatabase

# Stringify datetie format
def current_timestamp(format_pattern='%y_%m_%d_%H%M%S'):
    return datetime.now().strftime(format_pattern)

class ChatGPTThread(QThread):
    requestFinished = pyqtSignal()
    updateConversation_signal = pyqtSignal(str, str, int)
    updateStatus_signal = pyqtSignal(str, str)
    clearInput_signal = pyqtSignal()
    
    def __init__(self, parent):
        super().__init__()
        self._stopped = True
        self.parent = parent
        self.mutex = parent.mutex
    
    # When we run t.start(), this method will be triggered
    def run(self):
        self._stopped = False
        response = None
        prompt_string = self.parent.message_input.toPlainText()
        

        # Create a text cursor
        with QMutexLocker(self.mutex):
            # text_cursor = self.parent.conversation_window.textCursor()
            # # Move the cursor to the end
            # text_cursor.movePosition(QTextCursor.MoveOperation.End)
            # # Set the cusor position as the current text window's cursor position
            # self.parent.conversation_window.setTextCursor(text_cursor)
            # # Insert the conversation by following the format
            # self.parent.conversation_window.insertHtml('<p style="colore:#5caa00"> <strong>[User]: </strong><br>')
            # self.parent.conversation_window.insertHtml(prompt_string)
            # self.parent.conversation_window.insertHtml('<br')
            # self.parent.conversation_window.insertHtml('<br')

            self.updateConversation_signal.emit('user', prompt_string, 0)
            
            # make an api call to OpenAI ChatGPT model
            max_tokens = self.parent.max_tokens.value()   
            temperature = float('{0: .2f}'.format(self.parent.temperature.value() / 100))
            try:
                while response is None:
                    response = self.parent.chatgpt.send_request(prompt_string.strip(), max_tokens, temperature)
                    if 'error' in response:
                        # self.parent.status.setStyleSheet('''
                        #     color: red;
                        # ''')
                        # self.parent.clear_input()
                        # self.parent.status.showMessage(response['error'].user_message)
                        self.clearInput_signal.emit()
                        self.updateStatus_signal.emit('error', str(response['error']))
                        return
                    else:
                        # self.parent.status.setStyle.setStyleSheet('''
                        #     color: white;
                        # ''')
                        
                        # # Create a text cursor
                        # text_cursor = self.parent.conversation_window.textCursor()
                        # # Move the cursor to the end
                        # text_cursor.movePosition(QTextCursor.MoveOperation.End)
                        # # Set the cusor position as the current text window's cursor position
                        # self.parent.converstion_window.setTextCursor(text_cursor)
                        # # Insert the conversation by following the format
                        # self.parent.conversation_window.insertHtml('<p style="colore:#fd9620"> <strong>[AI Assistant]: </strong><br>')
                        # self.parent.conversation_window.insertHtml(markdown_converted)
                        # self.parent.conversation_window.insertHtml('<br')
                        # self.parent.conversation_window.insertHtml('<br')

                        # self.parent.status.showMessage('Tokens used: {0}'.format(response['usage']))
                        # convert the markdown response to html
                        markdown_converted = markdown.markdown(response['content'].strip())

                        self.updateConversation_signal.emit('ai', markdown_converted, response['usage'])
                        
                        self.requestFinished.emit()
            except Exception as e:
                print(e)
            

class AIAssistant(QWidget):
    def __init__(self, parent=None):
        super().__init__()  
        self.chatgpt = ChatGPT(API_KEY)
        self.mutex = QMutex()
        self.t = ChatGPTThread(self)
        # Connect the clearInput signal
        self.t.clearInput_signal.connect(self.clear_input)

        # Connect the updateStatus signal
        self.t.updateStatus_signal.connect(self.update_status)

        # Connect the updateConversation signal
        self.t.updateConversation_signal.connect(self.update_conversation)

        self.layout = {}
        self.layout['main'] = QVBoxLayout()
        self.setLayout(self.layout['main'])

        self.init_ui()
        self.init_set_default_settings()
        self.init_configure_signals()
    
    # Method to manage the sider bar to adjus the temperature
    def init_ui(self):
        # add sub layout manager
        self.layout['inputs'] = QFormLayout()

        # add sliders 
        self.max_tokens = QSlider(
            Qt.Orientation.Horizontal, 
            minimum=10, 
            maximum=4096, 
            singleStep=500,
            pageStep=500,
            value=200,
            toolTip='Maximum token ChatGPT can consume'
        )
        self.temperature = QSlider(
            Qt.Orientation.Horizontal, 
            minimum=0, 
            maximum=200, 
            value=10,
            toolTip='Randomness of the response'
        )
        self.max_token_value = QLabel('0.0')
        self.layout['slider_layout'] = QHBoxLayout()
        self.layout['slider_layout'].addWidget(self.max_token_value)
        self.layout['slider_layout'].addWidget(self.max_tokens)
        self.layout['inputs'].addRow(QLabel('Token Limit:'), self.layout['slider_layout'])

        self.temperature_value = QLabel('0.0')
        self.layout['slider_layout2'] = QHBoxLayout()
        self.layout['slider_layout2'].addWidget(self.temperature_value)
        self.layout['slider_layout2'].addWidget(self.temperature)
        self.layout['inputs'].addRow(QLabel('Temperature:'), self.layout['slider_layout2'])

        # Add them to the inputs layout
        self.layout['main'].addLayout(self.layout['inputs'])

        # Making adjustable conversation window
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout['main'].addWidget(splitter)

        # conversation window
        self.conversation_window = QTextBrowser(openExternalLinks=True)
        self.conversation_window.setReadOnly(True)
        splitter.addWidget(self.conversation_window)

        # Organzie user input text box
        self.input_window = QWidget()
        self.layout['input_entry'] = QHBoxLayout(self.input_window)

        self.message_input = QTextEdit()
        # Set the textBox expand as the same ratio as the application
        self.message_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout['input_entry'].addWidget(self.message_input)

        # Create buttons
        self.btn_submit = QPushButton('&Submit', clicked=self.post_message)
        self.btn_clear = QPushButton('&Clear', clicked=self.reset_input)
        self.layout['buttons'] = QVBoxLayout()
        self.layout['buttons'].addWidget(self.btn_submit)
        self.layout['buttons'].addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout['input_entry'].addLayout(self.layout['buttons'])

        splitter.addWidget(self.input_window)
        splitter.setSizes([800, 200])

        # add status bar 
        self.status = QStatusBar()
        self.status.setStyleSheet('font-size: 12px; color: white;')
        self.layout['main'].addWidget(self.status)

    # change parameters value 
    def init_set_default_settings(self):
        # token slider
        self.max_tokens.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.max_tokens.setTickInterval(500)
        self.max_tokens.setTracking(True)
        self.max_token_value.setText('{0: ,}'.format(self.max_tokens.value()))

        # temperature slider
        self.temperature.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.temperature.setTickInterval(100)
        self.temperature.setTracking(True)
        self.temperature_value.setText('{0: .2f}'.format(self.temperature.value() / 100))

    # signgals 
    def init_configure_signals(self):
        # connect the labels to sliders
        # the line is say the whenever the slider is changing, change label text
        self.max_tokens.valueChanged.connect(lambda: self.max_token_value.setText('{0: ,}'.format(self.max_tokens.value())))
        self.temperature.valueChanged.connect(lambda: self.temperature_value.setText('{0: .2f}'.format(self.temperature.value() / 100)))

    # input message method - post
    def post_message(self):
        if not self.message_input.toPlainText():
            self.status.showMessage('The prompt is empty.')
            return
        else:
            self.status.clearMessage()

            self.btn_submit.setEnabled(False)
            self.btn_submit.setText('Waiting...')

            self.t.requestFinished.connect(self.clear_input)
            self.t.start()
    
    def clear_input(self):
        self.message_input.clear()

    def update_status(self, status_type, message):
        if status_type == 'error':
            self.status.setStyleSheet('color: red;')
        else:
            self.status.setStyleSheet('color: white;')
        self.status.showMessage(message)

    def update_conversation(self, sender, content, usage):
        if sender == 'user':
            color = "#5caa00"
            label = "[User]:"
        else:
            color = "#fd9620"
            label = "[AI Assistant]:"
            self.status.showMessage(f"Tokens used: {usage}")

        text_cursor = self.conversation_window.textCursor()
        text_cursor.movePosition(QTextCursor.MoveOperation.End)
        self.conversation_window.setTextCursor(text_cursor)
        self.conversation_window.insertHtml(f'<p style="color:{color}"> <strong>{label} </strong><br>')
        self.conversation_window.insertHtml(content)
        self.conversation_window.insertHtml('<br><br>')

    # input message method - reset
    def reset_input(self):
        self.message_input.clear()
        self.status.clearMessage()

    def clear_input(self):
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText('&Submit')
        self.message_input.clear()  

    # Change font size of the current tab
    def font_zoom_in(self):
        font = self.message_input.font()
        # increase font size only when current size is less than 30 pixel
        if font.pixelSize() < 30:
            print(font.pixelSize())
            self.message_input.setStyleSheet('font-size: {0}px'.format(font.pixelSize() + 2))
            self.conversation_window.setStyleSheet('font-size: {0}px'.format(font.pixelSize() + 2))

    def font_zoom_out(self):
        font = self.message_input.font()
        # increase font size only when current size is less than 30 pixel
        if font.pixelSize() > 5:
            self.message_input.setStyleSheet('font-size: {0}px'.format(font.pixelSize() - 2))
            self.conversation_window.setStyleSheet('font-size: {0}px'.format(font.pixelSize() - 2))
         
  
# Tab manager this is how you use it 
class TabManager(QTabWidget):
    plusClicked = pyqtSignal()
    def __init__(self, paraent=None):
        super().__init__(paraent)
        # add tab close button
        self.setTabsClosable(True)
        
        # Create the add tab button and implement signals
        self.add_tab_button = QToolButton(self, text='+')
        self.add_tab_button.clicked.connect(self.plusClicked)
        self.setCornerWidget(self.add_tab_button)
        
        self.tabCloseRequested.connect(self.closeTab)
    def closeTab(self, tab_index):
        if self.count() == 1:
            return 
        self.removeTab(tab_index)

# Create the app window
class AppWindow(QWidget):
    # Think QWidegt is a blank window, where you can place alot of widgets 
    def __init__(self):
        super().__init__()
        self.window_width, self.window_height = 720, 720
        self.setMinimumSize(self.window_width, self.window_height)
        self.setWindowIcon(QIcon(os.path.join(os.getcwd(), 'app_icon.png'))) # The Python way to get the full path of a file in the current working directory
        self.setWindowTitle('Learned English Words Notebook v1')
        self.setStyleSheet('''
            QWidget {
                font-size 15px;
            }
        ''')
        self.tab_index_tracker = 1
        self.layout = {}

        # Main layout object
        # Vertical box layout manager
        self.layout['main'] = QVBoxLayout()
        self.setLayout(self.layout['main'])

        # Add spacing above the tab_manager
        # We use the index 0 is because tab_manager is the first widget added to the main layout
        self.layout['main'].insertSpacing(0, 19)


        self.init_ui()
        self.init_configure_signal()
        self.init_menu()
 
    def init_ui(self):
        # add tab manager
        self.tab_manager = TabManager()
        self.layout['main'].addWidget(self.tab_manager)

        ai_assistant = AIAssistant()
        self.tab_manager.addTab(ai_assistant, f'Conversation #{self.tab_index_tracker}')
        self.set_tab_focus()

    def set_tab_focus(self):
        activate_tab = self.tab_manager.currentWidget()
        # activate_tab.message_input.setFocus()

    def add_tab(self):
        self.tab_index_tracker += 1
        ai_assistant = AIAssistant()
        self.tab_manager.addTab(ai_assistant, f'Conversation #{self.tab_index_tracker}')
        self.tab_manager.setCurrentIndex(self.tab_manager.count()-1)
        self.set_tab_focus()

    def init_menu(self):
        # QMenuBar is a menu window
        self.menu_bar = QMenuBar(self)

        # The menu section, and which parent holds the submenu

        # File section menu
        file_menu = QMenu('&File', self.menu_bar)
        # Add submenu and corresponding action to the section
        file_menu.addAction('&Save output').triggered.connect(self.save_output)
        file_menu.addAction('&Insert chat history to DB').triggered.connect(self.save_conversation_log_to_db) 
        self.menu_bar.addMenu(file_menu)

        # view menu
        view_menu = QMenu('&View', self.menu_bar)
        view_menu.addAction('Zoom &in').triggered.connect(self.zoom_in)
        view_menu.addAction('Zoom &out').triggered.connect(self.zoom_out)
        self.menu_bar.addMenu(view_menu)
    
    def init_configure_signal(self):
        self.tab_manager.plusClicked.connect(self.add_tab)

    def save_output(self):
        # Let it know which is the currently focused window
        active_tab = self.tab_manager.currentWidget()
        # Convert the conversation in the window to plain text
        conversation_window_log = active_tab.conversation_window.toPlainText()
        timestamp = current_timestamp()
        with open('{0}_Chatlog.txt'.format(timestamp), 'w', encoding='UTF-8') as _f:
            _f.write(conversation_window_log)
        active_tab.status.showMessage('''File save at {0}/chat_log/{1}_Chatlog.txt'''.format(os.getcwd(), timestamp))

    def save_conversation_log_to_db(self):
        # Convert the conversation history to SQLite db
        # You need to use specific format by using inser_record method defined in db.py
        timestamp = current_timestamp('%Y-%m-%d, %H:%M:%S')
        active_tab = self.tab_manager.currentWidget()
        messages = str(active_tab.chatgpt.messages).replace("'", "''")
        values = f"{messages}', '{timestamp}'"

        db.insert_record('message_logs', 'messages, created_time', values)
        active_tab.status.showMessage('Record inserted')
        
    def closeEvent(self, event):
        """
        QWidget Close Event
        """
        db.close()
        
        # close threads
        for window in self.findChildren(AIAssistant):
            window.t.quit()

    def zoom_in(self):
        active_tab = self.tab_manager.currentWidget()
        active_tab.font_zoom_in()

    def zoom_out(self):
        active_tab = self.tab_manager.currentWidget()
        active_tab.font_zoom_out()


if __name__ == '__main__':
    # Load opneAI api key 
    config = ConfigParser()
    config.read('api_keys.ini')
    API_KEY = config.get('openai', 'API_KEY')

    # init ChatGPT SQlite database
    db = ChatGPTDatabase('english-dict.db')
    db.create_table(
        'message_logs ',
        '''
            message_long_no INTEGER PRIMARY KEY AUTOINCREMENT,
            messages TEXT,
            created TEXT
        '''
    )  

    # When running a desktop app, we need to create an applicatio instance in order it to running in the background 
    app = QApplication(sys.argv)
    app.setStyle('fusion') # fusion is the more Update-to-date style

    # The CSS style sheet
    qss_style = open(os.path.join(os.getcwd(), 'css_skins/style.qss'), 'r')
    app.setStyleSheet(qss_style.read())

    # lauch app window
    app_window = AppWindow()
    app_window.show()

    sys.exit(app.exec())
