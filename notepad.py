from tkinter import *
from tkinter import ttk, filedialog, simpledialog, messagebox
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import json
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import BBCodeFormatter
from pygments.styles import get_style_by_name

# Configuration
CONFIG_FILE = "notepad_config.json"
AUTO_SAVE_INTERVAL = 300000  # 5 minutes in milliseconds

# Define the main application window
win = Tk()
win.geometry("600x600")
win.title('Notepad')
#win.iconbitmap('notepad_icon.ico')

# Create a notebook for tabs
notebook = ttk.Notebook(win)
notebook.pack(expand=1, fill=BOTH)

# Variable to track current theme and other settings
current_theme = "light"  # default theme
show_line_numbers = True  # default line numbers setting
auto_save_enabled = True  # default auto-save setting

# Dictionary to track file paths for each tab
tab_file_paths = {}

# Variable to track split screen state
split_screen_active = False
split_screen_window = None

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                global current_theme, show_line_numbers, auto_save_enabled
                current_theme = config.get('theme', 'light')
                show_line_numbers = config.get('show_line_numbers', True)
                auto_save_enabled = config.get('auto_save', True)
    except Exception as e:
        print(f"Error loading config: {e}")

def save_config():
    try:
        config = {
            'theme': current_theme,
            'show_line_numbers': show_line_numbers,
            'auto_save': auto_save_enabled
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

# Function to create a new tab
def new_file():
    # Create a frame to hold text area and line numbers
    frame = Frame(notebook)
    frame.pack(fill='both', expand=True)
    
    # Create a sub-frame for better control of widget placement
    text_frame = Frame(frame)
    text_frame.pack(side='left', fill='both', expand=True)
    
    # Create main text area
    text_area = Text(text_frame, wrap="word", undo=True, font=("Arial", 12))
    text_area.pack(side='left', fill='both', expand=True)
    
    # Create line numbers text widget with fixed width font
    line_numbers = Text(frame, width=6, padx=3, takefocus=0, border=0,
                       background='#f0f0f0', state='disabled',
                       font=("Courier New", 12))
    if show_line_numbers:
        line_numbers.pack(side='right', fill='y')

    # Add scrollbar to text_frame
    scrollbar = Scrollbar(text_frame, orient='vertical', command=text_area.yview)
    scrollbar.pack(side='right', fill='y')
    
    # Configure text area scrolling
    def on_text_scroll(*args):
        if show_line_numbers:
            line_numbers.yview_moveto(args[0])
        scrollbar.set(*args)
    
    text_area.configure(yscrollcommand=on_text_scroll)
    line_numbers.configure(yscrollcommand=lambda *args: None)
    
    # Store references for later use
    frame.text_area = text_area
    frame.line_numbers = line_numbers
    text_area.line_numbers = line_numbers
    
    # Add the frame to a new tab
    notebook.add(frame, text="New Untitled Document")
    
    # Create a right-click menu for the tab
    create_tab_menu(text_area)
    
    # Create context menu for text area
    create_context_menu(text_area)
    
    # Apply current theme to new tab
    set_theme(current_theme)
    
    # Bind events for line numbers
    text_area.bind('<KeyPress>', lambda e: win.after(1, lambda: update_line_numbers(text_area)))
    text_area.bind('<KeyRelease>', lambda e: win.after(1, lambda: update_line_numbers(text_area)))
    text_area.bind('<MouseWheel>', lambda e: line_numbers.yview_moveto(text_area.yview()[0]) if show_line_numbers else None)
    text_area.bind('<Return>', lambda e: win.after(1, lambda: update_line_numbers(text_area)))
    text_area.bind('<BackSpace>', lambda e: win.after(1, lambda: update_line_numbers(text_area)))
    text_area.bind('<Delete>', lambda e: win.after(1, lambda: update_line_numbers(text_area)))
    
    # Initial line numbers
    update_line_numbers(text_area)
    
    # Setup auto-save
    if auto_save_enabled:
        setup_auto_save(text_area)
    
    return text_area

def update_line_numbers(text_area):
    if not show_line_numbers:
        return
        
    line_numbers = text_area.line_numbers
    line_numbers.configure(state='normal')
    line_numbers.delete('1.0', END)
    
    # Get the total number of lines
    contents = text_area.get('1.0', END)
    num_lines = contents.count('\n') + (not contents.endswith('\n'))
    
    # Create line numbers content with proper alignment
    line_numbers_content = '\n'.join(f'{i:4d}' for i in range(1, num_lines + 1))
    
    # Insert line numbers
    line_numbers.insert('1.0', line_numbers_content)
    
    # Sync scrolling
    text_area.yview_moveto(text_area.yview()[0])
    line_numbers.yview_moveto(text_area.yview()[0])
    
    line_numbers.configure(state='disabled')

def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    if file_path:
        text_area = new_file()
        with open(file_path, 'r') as file:
            text_area.insert(1.0, file.read())
        notebook.tab(notebook.index(text_area.master), text=file_path.split("/")[-1])  # Use file name as tab title
        tab_file_paths[notebook.index(text_area.master)] = file_path  # Store file path

def save_as_text():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, 'w') as file:
            file.write(current_text_area.get(1.0, END))
        notebook.tab(notebook.index(current_text_area.master), text=file_path.split("/")[-1])  # Update tab title
        tab_file_paths[notebook.index(current_text_area.master)] = file_path  # Store file path

def save_as_pdf():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]  # Get text area from frame
    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                            filetypes=[("PDF Files", "*.pdf"), 
                                                     ("All Files", "*.*")])
    if file_path:
        pdf_canvas = canvas.Canvas(file_path, pagesize=letter)
        text = current_text_area.get(1.0, END)
        
        # Configure text properties
        pdf_canvas.setFont("Helvetica", 12)
        y = 750  # Starting y position
        
        # Split text into lines and write each line
        for line in text.split('\n'):
            if y < 50:  # Check if we need a new page
                pdf_canvas.showPage()
                y = 750
                pdf_canvas.setFont("Helvetica", 12)
            
            pdf_canvas.drawString(72, y, line)
            y -= 15  # Move down for next line
            
        pdf_canvas.save()
        messagebox.showinfo("Save as PDF", f"Saved as PDF: {file_path}")

def save_as_batch_file():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    file_path = filedialog.asksaveasfilename(defaultextension=".bat", filetypes=[("Batch Files", "*.bat"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, 'w') as file:
            file.write(current_text_area.get(1.0, END))
        notebook.tab(notebook.index(current_text_area.master), text=file_path.split("/")[-1])  # Update tab title
        tab_file_paths[notebook.index(current_text_area.master)] = file_path  # Store file path

def save_as_command_prompt_file():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    file_path = filedialog.asksaveasfilename(defaultextension=".cmd", filetypes=[("Command Files", "*.cmd"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, 'w') as file:
            file.write(current_text_area.get(1.0, END))
        notebook.tab(notebook.index(current_text_area.master), text=file_path.split("/")[-1])  # Update tab title
        tab_file_paths[notebook.index(current_text_area.master)] = file_path  # Store file path

def exit_program():
    win.quit()

def get_current_text_area():
    frame = notebook.nametowidget(notebook.select())
    # Find the text area in the frame hierarchy
    for child in frame.winfo_children():
        if isinstance(child, Frame):  # text_frame
            for subchild in child.winfo_children():
                if isinstance(subchild, Text):
                    return subchild
    return None

def undo():
    text_area = get_current_text_area()
    if text_area:
        try:
            text_area.edit_undo()
        except:
            pass

def cut():
    text_area = get_current_text_area()
    if text_area:
        text_area.event_generate("<<Cut>>")

def copy():
    text_area = get_current_text_area()
    if text_area:
        text_area.event_generate("<<Copy>>")

def paste():
    text_area = get_current_text_area()
    if text_area:
        text_area.event_generate("<<Paste>>")

def delete():
    text_area = get_current_text_area()
    if text_area:
        text_area.event_generate("<<Clear>>")

def select_all():
    text_area = get_current_text_area()
    if text_area:
        text_area.tag_add("sel", "1.0", "end")

def insert_time_date():
    text_area = get_current_text_area()
    if text_area:
        text_area.insert(INSERT, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def find():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    find_text = simpledialog.askstring("Find", "Enter text to find:")
    if find_text:
        start_pos = current_text_area.search(find_text, "1.0", END)
        if start_pos:
            current_text_area.tag_add("highlight", start_pos, f"{start_pos}+{len(find_text)}c")
            current_text_area.tag_config("highlight", background="yellow")
        else:
            # Show a message box if the text is not found
            messagebox.showinfo("Not Found", f"'{find_text}' not found in the text.")

def replace():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    
    replace_window = Toplevel(win)
    replace_window.title("Replace")
    
    Label(replace_window, text="Find:").pack(side=LEFT, padx=5)
    entry_find = Entry(replace_window, width=30)
    entry_find.pack(side=LEFT, padx=5)
    
    Label(replace_window, text="Replace:").pack(side=LEFT, padx=5)
    entry_replace = Entry(replace_window, width=30)
    entry_replace.pack(side=LEFT, padx=5)
    
    def replace_text():
        find_text = entry_find.get()
        replace_text_value = entry_replace.get()  # Change variable name to avoid confusion
        content = current_text_area.get(1.0, END)
        
        # Check if the text to find exists in the content
        if find_text in content:
            new_content = content.replace(find_text, replace_text_value)
            current_text_area.delete(1.0, END)
            current_text_area.insert(1.0, new_content)
            replace_window.destroy()  # Close the replace window after replacing
        else:
            # Show a message box if the text is not found
            messagebox.showinfo("Not Found", f"'{find_text}' not found in the text.")

    Button(replace_window, text="Replace", command=replace_text).pack(side=LEFT, padx=5)

def find_all():
    current_text_area = notebook.nametowidget(notebook.select()).winfo_children()[1]
    find_window = Toplevel(win)
    find_window.title("Find All")
    find_window.geometry("300x100")
    
    Label(find_window, text="Find:").pack(pady=5)
    entry_find = Entry(find_window, width=30)
    entry_find.pack(pady=5)
    
    def highlight_all():
        # Remove existing highlights
        current_text_area.tag_remove("highlight", "1.0", END)
        
        find_text = entry_find.get()
        if find_text:
            pos = "1.0"
            count = 0
            while True:
                pos = current_text_area.search(find_text, pos, END)
                if not pos:
                    break
                count += 1
                end_pos = f"{pos}+{len(find_text)}c"
                current_text_area.tag_add("highlight", pos, end_pos)
                pos = end_pos
            
            current_text_area.tag_config("highlight", background="yellow")
            if count:
                messagebox.showinfo("Find Results", f"Found {count} occurrences")
            else:
                messagebox.showinfo("Find Results", "No matches found")
    
    Button(find_window, text="Find All", command=highlight_all).pack(pady=5)

def set_theme(theme):
    global current_theme
    current_theme = theme
    
    # Update all tabs
    for tab_id in notebook.tabs():
        frame = notebook.nametowidget(tab_id)
        text_area = None
        line_numbers = None
        
        # Find the text area and line numbers in the widget hierarchy
        for child in frame.winfo_children():
            if isinstance(child, Frame):  # text_frame
                for subchild in child.winfo_children():
                    if isinstance(subchild, Text):
                        text_area = subchild
            elif isinstance(subchild, Text):  # line numbers
                line_numbers = child
        
        if theme == "light":
            # Light theme colors
            win.configure(bg='white')
            notebook.configure(style='Light.TNotebook')
            text_area.configure(
                background='white',
                foreground='black',
                insertbackground='black',
                selectbackground='#0078D7',
                selectforeground='white'
            )
            if line_numbers:
                line_numbers.configure(
                    background='#f0f0f0',
                    foreground='gray'
                )
            
        else:
            # Dark theme colors
            win.configure(bg='#1e1e1e')
            notebook.configure(style='Dark.TNotebook')
            text_area.configure(
                background='#1e1e1e',
                foreground='#d4d4d4',
                insertbackground='white',
                selectbackground='#264f78',
                selectforeground='white'
            )
            if line_numbers:
                line_numbers.configure(
                    background='#252526',
                    foreground='#858585'
                )

# Configure notebook styles for themes
style = ttk.Style()
style.configure('Light.TNotebook', background='white')
style.configure('Dark.TNotebook', background='#1e1e1e')

def create_tab_menu(text_area):
    tab_menu = Menu(notebook, tearoff=0)
    tab_menu.add_command(label="Rename", command=lambda: rename_tab(notebook.index(text_area.master)))
    tab_menu.add_command(label="Close", command=lambda: close_tab(notebook.index(text_area.master)))

    # Bind the right-click event to the tab
    notebook.bind("<Button-3>", lambda event: tab_menu.post(event.x_root, event.y_root))

def create_context_menu(text_area):
    context_menu = Menu(text_area, tearoff=0)
    context_menu.add_command(label="Undo", command=undo)
    context_menu.add_separator()
    context_menu.add_command(label="Cut", command=cut)
    context_menu.add_command(label="Copy", command=copy)
    context_menu.add_command(label="Paste", command=paste)
    context_menu.add_command(label="Delete", command=delete)
    context_menu.add_separator()
    context_menu.add_command(label="Select All", command=select_all)
    
    def show_context_menu(event):
        context_menu.post(event.x_root, event.y_root)
    
    # Bind the right-click event to the text area
    text_area.bind("<Button-3>", show_context_menu)

def rename_tab(index):
    current_tab_text = notebook.tab(index, "text")  # Get current tab title
    tab_name = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=current_tab_text)
    if tab_name:
        notebook.tab(index, text=tab_name)  # Update tab title

def close_tab(index):
    notebook.forget(index)

def toggle_line_numbers():
    global show_line_numbers
    show_line_numbers = not show_line_numbers
    save_config()
    
    # Update all tabs
    for tab_id in notebook.tabs():
        frame = notebook.nametowidget(tab_id)
        
        # Find the text area in the frame hierarchy
        text_area = None
        for child in frame.winfo_children():
            if isinstance(child, Frame):  # text_frame
                for subchild in child.winfo_children():
                    if isinstance(subchild, Text):
                        text_area = subchild
                        break
                if text_area:
                    break
        
        if not text_area:
            continue
            
        line_numbers = text_area.line_numbers
        
        if show_line_numbers:
            line_numbers.pack(side='right', fill='y')
            update_line_numbers(text_area)
        else:
            line_numbers.pack_forget()

def toggle_auto_save():
    global auto_save_enabled
    auto_save_enabled = not auto_save_enabled
    save_config()
    
    # Update all tabs
    for tab_id in notebook.tabs():
        frame = notebook.nametowidget(tab_id)
        text_area = frame.winfo_children()[1]
        if auto_save_enabled:
            setup_auto_save(text_area)

def apply_syntax_highlighting():
    current_frame = notebook.nametowidget(notebook.select())
    text_area = current_frame.winfo_children()[1]
    
    # Get file extension from tab name
    tab_text = notebook.tab(notebook.select(), "text")
    try:
        lexer = get_lexer_for_filename(tab_text)
    except:
        lexer = TextLexer()
    
    # Get text content
    content = text_area.get(1.0, END)
    
    # Apply highlighting
    formatter = BBCodeFormatter(style=get_style_by_name('monokai'))
    highlighted = highlight(content, lexer, formatter)
    
    # Update text area
    text_area.delete(1.0, END)
    text_area.insert(1.0, highlighted)

def create_split_screen():
    global split_screen_active, split_screen_window
    
    if split_screen_active:
        # If split screen is active, close it
        if split_screen_window:
            split_screen_window.destroy()
            split_screen_window = None
        split_screen_active = False
        return

    # Get list of open tabs
    open_tabs = []
    for tab_id in notebook.tabs():
        tab_text = notebook.tab(tab_id, "text")
        open_tabs.append((tab_id, tab_text))
    
    if len(open_tabs) < 2:
        messagebox.showwarning("Split Screen", "You need at least two open tabs to use split screen.")
        return

    # Create split screen window
    split_screen_window = Toplevel(win)
    split_screen_window.title("Split Screen View")
    split_screen_window.geometry("1200x600")
    
    # Create left and right frames
    left_frame = Frame(split_screen_window)
    left_frame.pack(side=LEFT, fill=BOTH, expand=True)
    
    right_frame = Frame(split_screen_window)
    right_frame.pack(side=RIGHT, fill=BOTH, expand=True)
    
    # Create comboboxes for tab selection
    left_combo = ttk.Combobox(left_frame, values=[tab[1] for tab in open_tabs])
    left_combo.pack(fill=X, padx=5, pady=5)
    left_combo.set(open_tabs[0][1])
    
    right_combo = ttk.Combobox(right_frame, values=[tab[1] for tab in open_tabs])
    right_combo.pack(fill=X, padx=5, pady=5)
    right_combo.set(open_tabs[1][1] if len(open_tabs) > 1 else open_tabs[0][1])
    
    # Create text areas
    left_text = Text(left_frame, wrap="word", undo=True, font=("Arial", 12))
    left_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
    
    right_text = Text(right_frame, wrap="word", undo=True, font=("Arial", 12))
    right_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
    
    # Function to update text content
    def update_text_content(event=None):
        # Update left text area
        left_tab_name = left_combo.get()
        left_tab_id = [tab[0] for tab in open_tabs if notebook.tab(tab[0], "text") == left_tab_name][0]
        left_content = notebook.nametowidget(left_tab_id).winfo_children()[1].get(1.0, END)
        left_text.delete(1.0, END)
        left_text.insert(1.0, left_content)
        
        # Update right text area
        right_tab_name = right_combo.get()
        right_tab_id = [tab[0] for tab in open_tabs if notebook.tab(tab[0], "text") == right_tab_name][0]
        right_content = notebook.nametowidget(right_tab_id).winfo_children()[1].get(1.0, END)
        right_text.delete(1.0, END)
        right_text.insert(1.0, right_content)
    
    # Bind combobox selection to update function
    left_combo.bind('<<ComboboxSelected>>', update_text_content)
    right_combo.bind('<<ComboboxSelected>>', update_text_content)
    
    # Initial content update
    update_text_content()
    
    # Function to sync scroll
    def sync_scroll(*args):
        left_text.yview_moveto(args[0])
        right_text.yview_moveto(args[0])
    
    # Add scrollbars
    left_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=sync_scroll)
    left_scrollbar.pack(side=RIGHT, fill=Y)
    left_text.configure(yscrollcommand=left_scrollbar.set)
    
    right_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=sync_scroll)
    right_scrollbar.pack(side=RIGHT, fill=Y)
    right_text.configure(yscrollcommand=right_scrollbar.set)
    
    # Function to handle window close
    def on_split_screen_close():
        global split_screen_active, split_screen_window
        split_screen_active = False
        split_screen_window.destroy()
        split_screen_window = None
    
    split_screen_window.protocol("WM_DELETE_WINDOW", on_split_screen_close)
    split_screen_active = True

def create_menu():
    menubar = Menu(win)
    
    # File Menu
    file_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New", command=new_file, accelerator="Ctrl+N")
    file_menu.add_command(label="Open", command=open_file, accelerator="Ctrl+O")
    file_menu.add_command(label="Save As Text", command=save_as_text, accelerator="Ctrl+S")
    file_menu.add_command(label="Save As PDF", command=save_as_pdf)
    file_menu.add_command(label="Save As Batch File", command=save_as_batch_file)
    file_menu.add_command(label="Save As CMD File", command=save_as_command_prompt_file)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=exit_program)
    
    # Edit Menu
    edit_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(label="Undo", command=undo, accelerator="Ctrl+Z")
    edit_menu.add_separator()
    edit_menu.add_command(label="Cut", command=cut, accelerator="Ctrl+X")
    edit_menu.add_command(label="Copy", command=copy, accelerator="Ctrl+C")
    edit_menu.add_command(label="Paste", command=paste, accelerator="Ctrl+V")
    edit_menu.add_command(label="Delete", command=delete, accelerator="Del")
    edit_menu.add_separator()
    edit_menu.add_command(label="Find", command=find, accelerator="Ctrl+F")
    edit_menu.add_command(label="Find All", command=find_all)
    edit_menu.add_command(label="Replace", command=replace, accelerator="Ctrl+H")
    edit_menu.add_separator()
    edit_menu.add_command(label="Select All", command=select_all, accelerator="Ctrl+A")
    edit_menu.add_command(label="Time/Date", command=insert_time_date, accelerator="F5")
    
    # View Menu
    view_menu = Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)
    view_menu.add_checkbutton(label="Line Numbers", command=toggle_line_numbers)
    view_menu.add_checkbutton(label="Auto Save", command=toggle_auto_save)
    view_menu.add_command(label="Apply Syntax Highlighting", command=apply_syntax_highlighting)
    view_menu.add_separator()
    view_menu.add_command(label="Split Screen", command=create_split_screen)
    
    # Theme submenu
    theme_menu = Menu(view_menu, tearoff=0)
    view_menu.add_cascade(label="Theme", menu=theme_menu)
    theme_menu.add_command(label="Light", command=lambda: set_theme("light"))
    theme_menu.add_command(label="Dark", command=lambda: set_theme("dark"))
    
    win.config(menu=menubar)
    
    # Bind keyboard shortcuts
    win.bind('<Control-n>', lambda e: new_file())
    win.bind('<Control-o>', lambda e: open_file())
    win.bind('<Control-s>', lambda e: save_as_text())
    win.bind('<Control-z>', lambda e: undo())
    win.bind('<Control-x>', lambda e: cut())
    win.bind('<Control-c>', lambda e: copy())
    win.bind('<Control-v>', lambda e: paste())
    win.bind('<Control-f>', lambda e: find())
    win.bind('<Control-h>', lambda e: replace())
    win.bind('<Control-a>', lambda e: select_all())
    win.bind('<F5>', lambda e: insert_time_date())

def setup_auto_save(text_area):
    def auto_save():
        if auto_save_enabled and text_area.edit_modified():
            if notebook.index(text_area.master) in tab_file_paths:
                file_path = tab_file_paths[notebook.index(text_area.master)]
                try:
                    with open(file_path, 'w') as file:
                        file.write(text_area.get(1.0, END))
                    text_area.edit_modified(False)
                except Exception as e:
                    print(f"Auto-save failed: {e}")
        
        # Schedule next auto-save
        win.after(AUTO_SAVE_INTERVAL, lambda: auto_save())
    
    # Start auto-save cycle
    win.after(AUTO_SAVE_INTERVAL, lambda: auto_save())

load_config()
create_menu()

# Create the initial tab
new_file()

# Start the application
win.mainloop()
