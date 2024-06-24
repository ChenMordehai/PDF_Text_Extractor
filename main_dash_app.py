import base64
import io
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import pytesseract
import pdftotext
from dash.exceptions import PreventUpdate
import PyInstaller

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\...\AppData\Local\Tesseract-OCR\tesseract.exe' # path to tesseract.exe


def pdf_to_images(pdf_b):
    """

    :param pdf_b: Bytes - pdf file in bytes
    :return: List[Image] - pdf in images
    """
    local_poppler_path = r'C:\...\Release-23.11.0-0\poppler-23.11.0\Library\bin' # path to local poppler
    return convert_from_bytes(pdf_b, poppler_path=local_poppler_path)


def extract_text_from_images(images):
    """
    extract text from images using pytesseract
    :param images: List[Image] - pdf in images
    :return: String - text from images
    """
    text_per_page = [pytesseract.image_to_string(image, lang='heb+eng') for image in images]
    return "\n".join(text_per_page)


def extract_text_from_pdf(file_content):
    """
    extracting text from pdf, using pdftotext package
    :param file_content: Bytes - pdf content in bytes
    :return: String - text from pdf
    """
    with io.BytesIO(file_content) as f:
        pdf = pdftotext.PDF(f)
        return "\n\n".join(pdf)


def get_pathology_body_parts(body):
    """
    get pathology report sub parts
    :param body: String - full text
    :return: Dictionary - dictionary of pathology report parts
    """
    body_parts_dict = {}
    # macro_desc
    macro_prefix_index = body.find("תאור מאקרוסקופי‪:‬‬")
    if macro_prefix_index != -1:
        body_parts_dict["Macroscopic Description"] = body[macro_prefix_index:]
        body = body[:macro_prefix_index]

    # diagnosis
    diagnosis_prefix_index = body.find("אבחנה‪:‬‬")
    if diagnosis_prefix_index != -1:
        body_parts_dict["Diagnosis"] = body[diagnosis_prefix_index:]
        body = body[:diagnosis_prefix_index]

    # prev_tests
    prev_tests_prefix_index = body.find("‫בדיקות קודמות‪:")
    if prev_tests_prefix_index != -1:
        body_parts_dict["Previous Tests"] = body[prev_tests_prefix_index:]
        body = body[:prev_tests_prefix_index]

    # clinical_info
    clinical_info_prefix_index = body.find("‫פרטים קליניים‪:")
    if clinical_info_prefix_index != -1:
        body_parts_dict["Clinical Information"] = body[clinical_info_prefix_index:]
        body = body[:clinical_info_prefix_index]

    ans_body_parts_dict = {}
    if clinical_info_prefix_index != -1:
        ans_body_parts_dict["Clinical Information"] = body_parts_dict.get("Clinical Information")
    if prev_tests_prefix_index != -1:
        ans_body_parts_dict["Previous Tests"] = body_parts_dict.get("Previous Tests")
    if diagnosis_prefix_index != -1:
        ans_body_parts_dict["Diagnosis"] = body_parts_dict.get("Diagnosis")
    if macro_prefix_index != -1:
        ans_body_parts_dict["Macroscopic Description"] = body_parts_dict.get("Macroscopic Description")
    return ans_body_parts_dict


def get_partial_content(original_content):
    """
    get pathology report parts
    :param original_content: String - full text
    :return: Dictionary - dictionary of pathology report parts
    """
    header, body, footer = """""", """""", """"""
    prefix_options = ["‫פרטים קליניים‪:", "בדיקות קודמות‪:‬‬", "‫אבחנה‪:‬‬"]
    for p in prefix_options:
        prefix_index = original_content.find(p)
        if prefix_index != -1:
            header = original_content[:prefix_index]
            body = original_content[prefix_index:]
            break
    postfix_index = body.find("תאריך הדפסה‪:‬‬")
    footer = body[postfix_index:]
    body = body[:postfix_index]
    body_parts = get_pathology_body_parts(body)
    head_foot = {'General Information': header}
    z = head_foot.copy()
    z.update(body_parts)
    z['Document Footer Information'] = footer
    return z


def extract_children_values(data):
    """
    helper function for extracting values from dictionary before saving
    :param data: Dictionary
    :return: String - extracted string
    """
    result = []

    def recurse(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if key == 'children' and isinstance(value, str):
                    result.append(value)
                elif isinstance(value, (dict, list)):
                    recurse(value)
        elif isinstance(item, list):
            for sub_item in item:
                recurse(sub_item)

    recurse(data)
    return "\n".join(result)


# Dash Layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

colors = {
    'background': '#15112b',
    'text1': '#000000',
    'primary': '#f48599',
    'secondary': '#f8b4c0',
    'tertiary': '#f05672',
    'quaternary': '#e6e6e6'
}

app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.Img(src='/assets/logo.png', className="img-fluid mx-auto d-block mb-4",
                         style={'border-radius': '10%'}), width=12, className="text-center")
    ),
    dbc.Row(
        dbc.Col(
            dbc.Tabs([
                dbc.Tab(label='Text from PDF/Image', tab_id='tab-1',
                        # active_tab_style={'backgroundColor': colors['tertiary']},
                        active_label_style={'backgroundColor': colors['tertiary']},
                        label_style={'font-size': '20px'},
                        style={
                            'width': '75%', 'margin': 'auto', 'font-size': '20px'
                        },
                        children=[
                            html.Div(
                                """Select a PDF file or an image with text that you want to extract.\nThe text can be viewed and edited if necessary.\nYou can save the result as a text file.""",
                                style={'color': '#ffffff', 'whiteSpace': 'pre-wrap', 'font-size': '20px',
                                       'margin': '5%'}),
                            dcc.Upload(id='upload-file-tab1', children=html.Div([
                                '[Drag & Drop or ',
                                html.A('Select File'),
                                ']'
                            ]), style={
                                'width': '50%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'margin': 'auto',
                                'backgroundColor': colors['quaternary']
                            }),
                            html.Div(id='output-text-tab1', style={
                                'border': '1px solid #ddd',
                                'padding': '10px',
                                'minHeight': '400px',
                                'maxHeight': '400px',  # Maximum height for scrolling
                                'marginTop': '10px',
                                'whiteSpace': 'pre-wrap',  # This ensures newlines are respected
                                'backgroundColor': colors['quaternary'],
                                'color': colors['background'],
                                'overflowY': 'scroll'  # Add vertical scrollbar
                            }),
                            dbc.Button("Save Output", id='save-button-tab1', color='primary', className="mt-4"),
                            dcc.Download(id="download-text-tab1")
                        ]),
                dbc.Tab(label="Text from Pathology Report", tab_id='tab-2', id='tab-2',
                        active_label_style={'backgroundColor': colors['tertiary']},
                        label_style={'font-size': '20px'},
                        style={
                            'width': '75%', 'margin': 'auto', 'font-size': '20px'
                        }, children=[

                        html.Div(
                            """Extracting text according to the structure of a pathological report.\nThe text can be viewed and edited if necessary.\nYou can save the result as a text file.""",
                            style={'color': '#ffffff', 'whiteSpace': 'pre-wrap', 'font-size': '20px', 'margin': '5%'}),
                        dcc.Upload(id='upload-file-tab2', children=html.Div([
                            '[Drag & Drop or ',
                            html.A('Select File'),
                            ']'
                        ]), style={
                            'width': '50%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': 'auto',
                            'backgroundColor': colors['quaternary']
                        }),

                        dbc.Button("Save Output", id='save-button-tab2', color='primary', className="mt-4"),
                        dcc.Download(id="download-text-tab2")
                    ])

            ]),
            width=12,
            className="mt-4",
            style={'margin': 'auto', 'width': '75%'}
        )
    )
], fluid=True, style={'backgroundColor': colors['background'], 'color': colors['text1'], 'padding': '20px'})


# Callback Functions
@app.callback(
    Output('output-text-tab1', 'children'),
    Input('upload-file-tab1', 'contents'),
    State('upload-file-tab1', 'filename')
)
def update_output_tab1(file_content, file_name):
    if file_content is None:
        raise PreventUpdate

    content_type, content_string = file_content.split(',')
    decoded = base64.b64decode(content_string)

    if file_name.lower().endswith('.pdf'):
        text = extract_text_from_pdf(decoded)
        if not text.strip() or len(text) < 20:
            images = pdf_to_images(decoded)
            text = extract_text_from_images(images)
    else:
        raise PreventUpdate

    return text


@app.callback(
    Output('tab-2', 'children'),
    Input('upload-file-tab2', 'contents'),
    State('upload-file-tab2', 'filename'),
    State('tab-2', 'children')
)
def update_output_tab2(file_content, file_name, tab2_children):
    if file_content is None:
        raise PreventUpdate

    content_type, content_string = file_content.split(',')
    decoded = base64.b64decode(content_string)

    if file_name.lower().endswith('.pdf'):
        text = extract_text_from_pdf(decoded)
        if not text.strip() or len(text) < 20:
            images = pdf_to_images(decoded)
            text = extract_text_from_images(images)
    else:
        raise PreventUpdate

    text = f"'\u202B'{text}'\u202C'"
    ans_parts = get_partial_content(text)
    new_cards = []
    for title, content in ans_parts.items():
        new_card = dbc.Card(
            [
                dbc.CardHeader(f"{title}", style={'color': colors['secondary'], 'backgroundColor': '#464545',
                                                  'font-weight': 'bold'}),
                dbc.CardBody(f"{content}", style={'backgroundColor': colors['quaternary'], 'color': '#000000'})
            ]
            # className="mb-3"
        )
        new_cards.append(new_card)
    new_div = html.Div(children=new_cards,
                       id=f'output-text-tab2-content', style={
            'border': '1px solid #ddd',
            'padding': '10px',
            'minHeight': '200px',
            'maxHeight': '600px',  # Maximum height for scrolling
            'marginTop': '10px',
            'whiteSpace': 'pre-wrap',
            'backgroundColor': colors['quaternary'],
            'color': colors['background'],
            'overflowY': 'scroll'  # Add vertical scrollbar
        })

    if tab2_children:
        for child in tab2_children:
            if child['type'] == 'Div':
                tab2_children.remove(child)
                break
        tab2_children.append(new_div)
        return tab2_children

    return new_div


@app.callback(
    Output("download-text-tab1", "data"),
    Input("save-button-tab1", "n_clicks"),
    State("output-text-tab1", "children"),
    prevent_initial_call=True,
)
def save_text_tab1(n_clicks, text):
    if not text:
        raise PreventUpdate
    # Convert HTML breaks back to newlines
    plain_text = text.replace('<br>', '\n')
    return dict(content=plain_text, filename="extracted_text_tab1.txt")


@app.callback(
    Output("download-text-tab2", "data"),
    Input("save-button-tab2", "n_clicks"),
    State("output-text-tab2-content", "children"),
    prevent_initial_call=True,
)
def save_text_tab2(n_clicks, text):
    if not text:
        raise PreventUpdate
    text = extract_children_values(text)
    # Convert HTML breaks back to newlines
    plain_text1 = text.replace('<br>', '\n')
    return dict(content=plain_text1, filename="extracted_text_tab2.txt")


if __name__ == '__main__':
    app.run_server(debug=True)
