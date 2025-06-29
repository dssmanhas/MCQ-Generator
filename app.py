from flask import Flask,request,render_template,send_file
import os
import pdfplumber
#pip install python_docx
import docx
from werkzeug.utils import secure_filename
import google.generativeai as genai
#pip install fpdf
from fpdf import FPDF
os.environ["GOOGLE_API_KEY"] = "AIzaSyDogMeRkGgbIIvub-zMf1sazHSI7ZRc2Ho"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model=genai.GenerativeModel("gemini-1.5-flash")
app=Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['RESULTS_FOLDER']='results/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx','txt'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
def extract_text_from_file(file_path):
    ext=file_path.rsplit(".",1)[1].lower()
    if ext == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() + '\n'
        return text
    elif ext == 'docx':
        doc = docx.Document(file_path)
        text = ''.join([para.text for para in doc.paragraphs])
        return text
    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    return None
def Question_mcqs_generator(text,num_questions):
    prompt = f"""Generate {num_questions} multiple choice questions based on the following text:\n{text}
    Each question should have one correct answer and three distractors. Format the output as follows:\n1. Question?\n   a) Option A\n   b) Option B\n   c) Option C\n   d) Option D\nCorrect Answer: [letter of the correct option]"""
    response=model.generate_content(prompt).text.strip()
    return response
def save_mcqs_to_file(mcqs, filename):
    file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    with open(file_path,'w') as f:
        f.write(mcqs)
    return file_path

def create_pdf(mcqs, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for mcq in mcqs.split('\n'):
        if mcq.strip():  # Check if the line is not empty
            pdf.multi_cell(0, 10, mcq.strip())
            pdf.ln(5)
    pdf_file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    pdf.output(pdf_file_path)
    return pdf_file_path
@app.route("/")
def index():
    return render_template("input.html")

@app.route("/generate",methods=['POST'])
def generate_mcqs():
    if 'file' not in request.files:
        return "No file part in the request"
    file=request.files['file']
    num_questions=request.form['num_questions']
    if file and allowed_file(file.filename):
        filename=secure_filename(file.filename)
        file_path=os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        text=extract_text_from_file(file_path)
        if text:
            num_questions=int(request.form['num_questions'])
            mcqs=Question_mcqs_generator(text,num_questions)
            txt_filename=f"generated_mcqs_{filename.rsplit('.', 1)[0]}.txt"
            pdf_filename=f"generated_mcqs_{filename.rsplit('.', 1)[0]}.pdf"
            save_mcqs_to_file(mcqs,txt_filename)
            create_pdf(mcqs,pdf_filename)
            parsed_mcqs = parse_mcqs(mcqs)
            return render_template("result.html", mcqs=parsed_mcqs, txt_filename=txt_filename, pdf_filename=pdf_filename)
    return "invalid file format or empty file"
def parse_mcqs(mcqs_text):
    mcqs = []
    for block in mcqs_text.strip().split('\n\n'):
        lines = block.strip().split('\n')
        if len(lines) < 6:  # 1 question + 4 options + 1 correct answer
            continue
        question = lines[0]
        options = lines[1:5]
        correct_answer = lines[5].replace('Correct Answer:', '').strip()
        mcqs.append({'question': question, 'options': options, 'correct_answer': correct_answer})
    return mcqs

# In your generate_mcqs function, before render_template:
@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)
if __name__=="__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['RESULTS_FOLDER']):
        os.makedirs(app.config['RESULTS_FOLDER'])
    app.run(debug=True)