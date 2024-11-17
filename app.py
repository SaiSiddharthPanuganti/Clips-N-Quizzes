import tkinter as tk
from tkinter import messagebox, scrolledtext, Toplevel, ttk,filedialog, messagebox, simpledialog
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import json
from fpdf import FPDF

api_key = "AIzaSyCOZh59AMq_WVWUD8swvAKs_KKoN9ruB9o"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Quiz Generator")
        self.root.geometry("500x400")

        self.video_link = ""
        self.num_questions = 0
        self.quiz_type = 'Multiple Choice' 
        self.questions_dict = {}
        self.current_question = 0
        self.user_answers = {}

        # Layout
        tk.Label(root, text="YouTube Video Link:").pack(pady=5)
        self.video_link_entry = tk.Entry(root, width=50)
        self.video_link_entry.pack(pady=5)

        tk.Label(root, text="Number of Questions:").pack(pady=5)
        self.num_questions_entry = tk.Entry(root, width=5)
        self.num_questions_entry.pack(pady=5)

        # Quiz Type Selection
        tk.Label(root, text="Select Quiz Type:").pack(pady=5)
        self.quiz_type_var = tk.StringVar(value="Multiple Choice")
        self.quiz_type_combobox = ttk.Combobox(root, textvariable=self.quiz_type_var,
                                               values=["Multiple Choice", "Fill in the Blanks", "True or False"])
        self.quiz_type_combobox.pack(pady=5)

        # Difficulty Level Selection
        tk.Label(root, text="Select Difficulty Level:").pack(pady=5)
        self.difficulty_var = tk.StringVar(value="Easy")
        self.difficulty_combobox = ttk.Combobox(root, textvariable=self.difficulty_var,
                                                values=["Easy", "Medium", "Hard"])
        self.difficulty_combobox.pack(pady=5)

        # Generate Quiz Button
        generate_button = tk.Button(root, text="Generate Quiz", command=self.generate_quiz)
        generate_button.pack(pady=20)

        # Show Transcript Button
        transcript_button = tk.Button(root, text="Show Transcript", command=self.show_transcript)
        transcript_button.pack(pady=5)

    def generate_quiz_title(self):
        if not self.questions_dict:
            return "YouTube Video Quiz"

        # Prepare the prompt for the AI model
        prompt = "Based on the following quiz questions, generate a short, descriptive title for this quiz:\n\n"
        for q_num, q_data in self.questions_dict.items():
            prompt += f"Question {q_num}: {q_data['question']}\n"

        try:
            response = model.generate_content(prompt)
            title = response.text.strip()
            return title if title else "YouTube Video Quiz"
        except Exception as e:
            print(f"Error generating title: {e}")
            return "YouTube Video Quiz"

    def open_save_options(self, on_save_complete_callback=None):
        if not self.questions_dict:
            messagebox.showerror("Error", "No quiz has been generated yet.")
            return

        def save_and_close():
        # Save the questions and close the save window
            self.save_questions(file_format.get(), save_window)
            save_window.destroy()

        # Call the callback after the save window is closed
            if on_save_complete_callback:
                on_save_complete_callback()

        save_window = Toplevel(self.root)
        save_window.title("Save Quiz")
        save_window.geometry("300x150")

        tk.Label(save_window, text="Select file format:").pack(pady=10)

        file_format = tk.StringVar(value="json")
        tk.Radiobutton(save_window, text="JSON", variable=file_format, value="json").pack()
        tk.Radiobutton(save_window, text="PDF", variable=file_format, value="pdf").pack()

        tk.Button(save_window, text="Save", command=save_and_close).pack(pady=20)

    def save_questions(self, file_format, save_window):

        # Set up file dialog based on chosen format
        if file_format == 'json':
            file_types = [('JSON files', '*.json')]
            default_extension = ".json"
        else:  # pdf
            file_types = [('PDF files', '*.pdf')]
            default_extension = ".pdf"

        file_path = filedialog.asksaveasfilename(filetypes=file_types, defaultextension=default_extension)
        
        if not file_path:
            return  # User cancelled the save operation

        # Generate a title for the quiz
        quiz_title = self.generate_quiz_title()

        if file_path.endswith('.json'):
            with open(file_path, 'w') as f:
                json.dump({"title": quiz_title, "questions": self.questions_dict}, f, indent=2)
        elif file_path.endswith('.pdf'):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=16)
            pdf.cell(200, 10, txt=quiz_title, ln=True, align='C')
            pdf.set_font("Arial", size=12)
            
            for q_num, q_data in self.questions_dict.items():
                pdf.cell(200, 10, txt=f"Question {q_num}: {q_data['question']}", ln=True)
                if 'options' in q_data:
                    for option in q_data['options']:
                        pdf.cell(200, 10, txt=f"- {option}", ln=True)
                pdf.cell(200, 10, txt=f"Correct Answer: {q_data['correct_answer']}", ln=True)
                pdf.cell(200, 10, txt="", ln=True)  # Empty line for spacing
            
            pdf.output(file_path)

        messagebox.showinfo("Success", f"Questions saved to {file_path}")
        save_window.destroy()

    def generate_quiz(self):
        self.video_link = self.video_link_entry.get().strip()
        if not self.video_link:
            messagebox.showerror("Error", "Please enter a valid YouTube video link.")
            return

        try:
            self.num_questions = int(self.num_questions_entry.get())
            if self.num_questions <= 0:
                raise ValueError("Number of questions must be a positive integer.")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive integer for the number of questions.")
            return

        self.quiz_type = self.quiz_type_var.get()
        self.difficulty = self.difficulty_var.get()

        transcript = summarize_video(self.video_link)
        if not transcript:
            messagebox.showerror("Error", "Failed to retrieve transcript. Please check the video link.")
            return

        try:
            self.questions_dict = generate_quiz_from_transcript(transcript, self.num_questions, self.quiz_type, self.difficulty)
        except (json.JSONDecodeError, IndexError):
            messagebox.showerror("Error", "Failed to generate quiz. Try again with a valid transcript or quiz type.")
            return

        # Ask user if they want to save before attempting
        save_choice = messagebox.askyesnocancel("Save Questions", "Do you want to save the questions before attempting the quiz?")
        
        if save_choice is None:  # User clicked Cancel
            return
        elif save_choice:  # User clicked Yes
        # Open save options and proceed to quiz only after saving
            self.open_save_options(on_save_complete_callback=self.open_quiz_window)
        else:  # User clicked No
        # Open the quiz window directly
            self.current_question = 0
            self.user_answers = {}  # Reset previous answers
            self.open_quiz_window()

    def open_quiz_window(self):
        # Create a new Toplevel window for the quiz
        self.quiz_window = Toplevel(self.root)
        self.quiz_window.title("Quiz Window")
        self.quiz_window.geometry("500x400")

        self.question_label = tk.Label(self.quiz_window, text="", wraplength=450)
        self.question_label.pack(pady=10)

        # Reset the options_var to prevent pre-selection
        self.options_var = tk.StringVar(value=-1)  # Reset to blank for no selection
        self.answer_entry = None

        if self.quiz_type == "Multiple Choice":
            self.option_buttons = []
            for i in range(4):
                rb = tk.Radiobutton(self.quiz_window, text="", variable=self.options_var, value=str(i), wraplength=450)
                rb.pack(anchor="w", padx=20)
                self.option_buttons.append(rb)
        elif self.quiz_type == "Fill in the Blanks":
            self.answer_entry = tk.Entry(self.quiz_window, width=50)
            self.answer_entry.pack(pady=10)
        elif self.quiz_type == "True or False":
            self.option_buttons = []
            for option in ["True", "False"]:
                rb = tk.Radiobutton(self.quiz_window, text=option, variable=self.options_var, value=option,
                                    wraplength=450)
                rb.pack(anchor="w", padx=20)
                self.option_buttons.append(rb)

        # Navigation Buttons
        self.prev_button = tk.Button(self.quiz_window, text="Previous", command=self.prev_question)
        self.prev_button.pack(side="left", padx=20, pady=20)

        self.next_button = tk.Button(self.quiz_window, text="Next", command=self.next_question)
        self.next_button.pack(side="right", padx=20, pady=20)

        # Submit Button (Initially hidden)
        self.submit_button = tk.Button(self.quiz_window, text="Submit", command=self.submit_quiz)
        self.submit_button.pack_forget()

        self.show_question()

    def show_transcript(self):
        transcript = summarize_video(self.video_link)
        if not transcript:
            messagebox.showerror("Error", "Could not retrieve transcript.")
            return

        transcript_window = Toplevel(self.root)
        transcript_window.title("Video Transcript")
        transcript_window.geometry("400x300")
        transcript_text = scrolledtext.ScrolledText(transcript_window, wrap=tk.WORD)
        transcript_text.insert(tk.END, transcript)
        transcript_text.config(state=tk.DISABLED)  # Make it read-only
        transcript_text.pack(expand=True, fill='both')

    def show_question(self):
    # Get the current question data
        question_data = self.questions_dict.get(str(self.current_question + 1), None)
        if not question_data:
            return

        question_text = question_data['question']
        self.question_label.config(text=f"Question {self.current_question + 1}: {question_text}")

        # Reset the options_var to an empty string for fresh input
        self.options_var.set(-1)  # Reset selection for new question
        
        if self.quiz_type == "Multiple Choice":
            options = question_data['options']
            for i, option in enumerate(options):
                self.option_buttons[i].config(text=option)

            # Restore previous answer if any
            if str(self.current_question) in self.user_answers:
                self.options_var.set(self.user_answers[str(self.current_question)])
        
        elif self.quiz_type == "Fill in the Blanks":
            self.answer_entry.delete(0, tk.END)  # Clear the entry field
            if str(self.current_question) in self.user_answers:
                self.answer_entry.insert(0, self.user_answers[str(self.current_question)])

        elif self.quiz_type == "True or False":
            # True or False only needs two options
            for i, option in enumerate(["True", "False"]):
                self.option_buttons[i].config(text=option)

            # Restore previous answer if any
            if str(self.current_question) in self.user_answers:
                self.options_var.set(self.user_answers[str(self.current_question)])

        # Show/hide buttons appropriately
        self.prev_button.config(state=tk.NORMAL if self.current_question > 0 else tk.DISABLED)
        if self.current_question == len(self.questions_dict) - 1:
            self.next_button.pack_forget()
            self.submit_button.pack(side="right", padx=20, pady=20)
        else:
            self.next_button.pack(side="right", padx=20, pady=20)
            self.submit_button.pack_forget()

    def next_question(self):
        if self.quiz_type == "Multiple Choice" or self.quiz_type == "True or False":
            selected_answer = self.options_var.get()
            if selected_answer is not None:
                self.user_answers[str(self.current_question)] = selected_answer
        elif self.quiz_type == "Fill in the Blanks":
            user_input = self.answer_entry.get().strip()
            self.user_answers[str(self.current_question)] = user_input

        self.current_question += 1
        self.show_question()

    def prev_question(self):
        if self.quiz_type == "Multiple Choice" or self.quiz_type == "True or False":
            selected_answer = self.options_var.get()
            if selected_answer is not None:
                self.user_answers[str(self.current_question)] = selected_answer
        elif self.quiz_type == "Fill in the Blanks":
            user_input = self.answer_entry.get().strip()
            self.user_answers[str(self.current_question)] = user_input

        self.current_question -= 1
        self.show_question()

    def submit_quiz(self):
        if self.quiz_type == "Multiple Choice" or self.quiz_type == "True or False":
            selected_answer = self.options_var.get()
            if selected_answer is not None:
                self.user_answers[str(self.current_question)] = selected_answer
        elif self.quiz_type == "Fill in the Blanks":
            user_input = self.answer_entry.get().strip()
            self.user_answers[str(self.current_question)] = user_input

        unattempted_questions = [f"Question {i + 1}" for i in range(len(self.questions_dict)) if
                                 str(i) not in self.user_answers]
        if unattempted_questions:
            warning = f"You have not attempted: {', '.join(unattempted_questions)}.\nDo you still want to submit?"
            proceed = messagebox.askyesno("Confirmation", warning)
            if not proceed:
                return

        self.evaluate_quiz()

    def evaluate_quiz(self):
        score = 0
        result_details = {}

        for i, question_data in self.questions_dict.items():
            question_num = int(i)
            question_text = question_data['question']
            correct_answer = question_data['correct_answer'].strip()
            user_answer = self.user_answers.get(str(question_num - 1), None)

            # Initialize correct flag and answer text for displaying
            is_correct = False
            user_answer_text = "Not answered"
            correct_answer_text = correct_answer

            # Determine answer based on quiz type
            if self.quiz_type == "Multiple Choice":
                options = question_data['options']
                correct_letter = correct_answer.upper()
                correct_text = options[ord(correct_letter) - ord('A')]

                if user_answer is not None:
                    user_letter = chr(65 + int(user_answer))
                    user_text = options[int(user_answer)]
                    is_correct = user_letter == correct_letter
                    user_answer_text = user_letter + ". " + user_text
                else:
                    user_answer_text = "Not answered"
                    is_correct = False

                result_details[question_num] = {
                    "question": question_text,
                    "your_answer": user_answer_text,
                    "correct_answer": correct_letter + ". " + correct_text,
                    "status": 'Correct!' if is_correct else 'Incorrect',
                    "is_correct": is_correct
                }

            elif self.quiz_type == "True or False":
                if user_answer is not None:
                    is_correct = user_answer.lower() == correct_answer.lower()
                    user_answer_text = user_answer
                else:
                    user_answer_text = "Not answered"
                    is_correct = False

                result_details[question_num] = {
                    "question": question_text,
                    "your_answer": user_answer_text,
                    "correct_answer": correct_answer,
                    "status": 'Correct!' if is_correct else 'Incorrect',
                    "is_correct": is_correct
                }

            elif self.quiz_type == "Fill in the Blanks":
                if user_answer is not None:
                    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
                    user_answer_text = user_answer.strip()
                else:
                    user_answer_text = "Not answered"
                    is_correct = False

                result_details[question_num] = {
                    "question": question_text,
                    "your_answer": user_answer_text,
                    "correct_answer": correct_answer,
                    "status": 'Correct!' if is_correct else 'Incorrect',
                    "is_correct": is_correct
                }

            # Increment score if answer is correct
            if is_correct:
                score += 1

        result_message = f"Your score: {score}/{len(self.questions_dict)}\n\n"

        # Create a new window to display the results
        result_window = Toplevel(self.root)
        result_window.title("Quiz Results")
        result_window.geometry("600x400")

        # Create a ScrolledText widget to display the results
        result_text = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, width=70, height=20)
        result_text.pack(padx=10, pady=10, expand=True, fill='both')

        # Insert the result message into the ScrolledText widget
        result_text.insert(tk.END, result_message)

        # Define color tags for answers
        result_text.tag_configure("correct_green", foreground="green")
        result_text.tag_configure("incorrect_red", foreground="red")
        result_text.tag_configure("user_answer_red", foreground="red")

        # Insert result details with appropriate tags
        for question_num, result in result_details.items():
            question_text = result["question"]
            user_answer_text = result["your_answer"]
            correct_answer_text = result["correct_answer"]
            status = result["status"]
            is_correct = result["is_correct"]

            # Add question
            result_text.insert(tk.END, f"Q{question_num}: {question_text}\n")

            # Add user's answer with color
            if is_correct:
                result_text.insert(tk.END, f"Your answer: {user_answer_text}\n", "correct_green")
            else:
                result_text.insert(tk.END, f"Your answer: {user_answer_text}\n", "user_answer_red")

            # Add correct answer with color
            result_text.insert(tk.END, f"Correct answer: {correct_answer_text}\n", "correct_green")

            # Add status (Correct! or Incorrect) with appropriate color
            if is_correct:
                result_text.insert(tk.END, f"{status}\n", "correct_green")
            else:
                result_text.insert(tk.END, f"{status}\n", "incorrect_red")

            result_text.insert(tk.END, "\n")  # Add a newline for spacing

        result_text.config(state=tk.DISABLED)  # Make it read-only

        # Create an OK button to close both the result window and the quiz window
        ok_button = ttk.Button(result_window, text="OK", command=lambda: self.close_quiz_windows(result_window))
        ok_button.pack(pady=10)


    def close_quiz_windows(self, result_window):
        result_window.destroy()
        self.quiz_window.destroy()
# Helper functions
def summarize_video(video_link):
    try:
        video_id = video_link.split("v=")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = ' '.join([entry['text'] for entry in transcript])
        return full_transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None


def generate_quiz_from_transcript(transcript, num_questions, quiz_type, difficulty):
    difficulty_prompts = {
        "Easy": "Generate straightforward questions with direct answers from the transcript.",
        "Medium": "Generate questions that require some inference or connecting information from different parts of the transcript.",
        "Hard": "Generate complex questions that may require deeper understanding, analysis, or application of concepts from the transcript. For technical topics, you may include questions about hypothetical scenarios, code outputs, or problem-solving using information from the transcript."
    }

    base_prompt = f"""
    Using the following transcript {transcript} from a YouTube video, generate a quiz with {num_questions} questions in the format of {quiz_type}. 
    Difficulty level: {difficulty}
    {difficulty_prompts[difficulty]}
    """

    if quiz_type == "Multiple Choice":
        prompt = base_prompt + """
        The response should be in valid JSON format where:
        - Each key is the question index (starting from 1).
        - Each value is another dictionary with the following structure:
          {
            "question": "Question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A"  # Correct answer option (A, B, C, or D)
          }
        """
    elif quiz_type == "Fill in the Blanks":
        prompt = base_prompt + """
        The response should be in valid JSON format where:
        - Each key is the question index (starting from 1).
        - Each value is another dictionary with the following structure:
          {
            "question": "Question with a blank space",
            "correct_answer": "Answer"
          }
        """
    elif quiz_type == "True or False":
        prompt = base_prompt + """
        The response should be in valid JSON format where:
        - Each key is the question index (starting from 1).
        - Each value is another dictionary with the following structure:
          {
            "question": "Question text",
            "correct_answer": "True/False"
          }
        """

    response = model.generate_content(prompt)
    quiz_text = response.candidates[0].content.parts[0].text
    cleaned_quiz_text = re.sub(r'```json|```', '', quiz_text).strip()
    return json.loads(cleaned_quiz_text)


# Main program

root = tk.Tk()
app = QuizApp(root)
root.mainloop()