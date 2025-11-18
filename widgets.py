from PyQt5.QtWidgets import QPushButton, QLineEdit, QComboBox, QLabel

def create_button(text, callback, object_name=None,width=300, height=30):
    button = QPushButton(text)
    button.clicked.connect(callback)
    button.setFixedSize(width,height)
    if object_name:
        button.setObjectName(object_name)
    return button

def create_text_input(placeholder, width=300, height=30):
    text_input = QLineEdit()
    text_input.setPlaceholderText(placeholder)
    text_input.setFixedSize(width, height)
    return text_input

def create_dropdown(items, callback, width=300, height=30):
    dropdown = QComboBox()
    item_list = list(items)
    dropdown.addItems(item_list)
    dropdown.setFixedSize(width, height)
    dropdown.currentIndexChanged.connect(lambda idx: callback(item_list[idx]))
    return dropdown

def create_label(text):
    return QLabel(text)
    


