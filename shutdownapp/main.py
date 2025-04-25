import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import mediapipe as mp
import speech_recognition as sr
import threading
import os
import platform
import json
import time  # Add this import

class ShutdownController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Smart Shutdown")
        self.root.geometry("400x400")  # Smaller window size
        
        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#4a7abc"
        self.root.configure(bg=self.bg_color)
        
        # Data file paths
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        self.gestures_file = os.path.join(self.data_dir, "gestures.json")
        self.voice_file = os.path.join(self.data_dir, "voice_commands.json")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # Initialize status variables
        self.is_listening = False
        self.is_detecting = False
        
        # Initialize recognizers
        self.speech_recognizer = sr.Recognizer()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7
        )
        
        # System actions mapping
        self.system_actions = {
            'shutdown': self.shutdown_system,
            'lock': self.lock_system
        }
        
        # Default voice commands
        self.voice_commands = {
            'shutdown': ['shutdown', 'turn off', 'power off'],
            'lock': ['lock', 'secure', 'lock screen']
        }
        
        # Load saved custom gestures and voice commands
        self.custom_gestures = self.load_data(self.gestures_file, {
            'shutdown': [],
            'lock': []
        })
        
        self.custom_voice_commands = self.load_data(self.voice_file, {
            'shutdown': [],
            'lock': []
        })
        
        # Setup the GUI
        self.setup_gui()
        
    def load_data(self, file_path, default_data):
        """Load data from JSON file or return default if file doesn't exist"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return default_data
        except Exception as e:
            print(f"Error loading data: {e}")
            return default_data
            
    def save_data(self, file_path, data):
        """Save data to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def setup_gui(self):
        # Create a style
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=6)
        style.configure("TLabel", font=("Arial", 11), background=self.bg_color)
        style.configure("TFrame", background=self.bg_color)
        style.configure("Header.TLabel", font=("Arial", 14, "bold"), background=self.bg_color)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10 10 10 10", style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Remove the app title
        # title_label = ttk.Label(main_frame, text="Smart Shutdown Control", style="Header.TLabel")
        # title_label.pack(pady=(0, 20))
        
        # Status Frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(
            status_frame,
            text="",  # Removed "System Ready" text
            font=("Arial", 12),
            foreground=self.accent_color
        )
        self.status_label.pack()
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.voice_button = ttk.Button(
            button_frame,
            text="Start Voice Recognition",
            command=self.toggle_voice_recognition,
            width=25
        )
        self.voice_button.pack(pady=5)
        
        self.gesture_button = ttk.Button(
            button_frame,
            text="Start Gesture Recognition",
            command=self.toggle_gesture_recognition,
            width=25
        )
        self.gesture_button.pack(pady=5)
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Gesture tab
        gesture_tab = ttk.Frame(notebook, padding=10)
        notebook.add(gesture_tab, text="Custom Gestures")
        
        # Voice tab
        voice_tab = ttk.Frame(notebook, padding=10)
        notebook.add(voice_tab, text="Voice Commands")
        
        # Custom Gesture Section
        for action in ['shutdown', 'lock']:
            frame = ttk.Frame(gesture_tab)
            frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame, text=f"{action.title()}:").pack(side=tk.LEFT, padx=(0, 10))
            
            # Remove the "saved" count text
            # count_text = f"{len(self.custom_gestures[action])} saved"
            # count_label = ttk.Label(frame, text=count_text)
            # count_label.pack(side=tk.LEFT, padx=(0, 10))
            
            save_button = ttk.Button(
                frame,
                text=f"Save New",
                command=lambda a=action: self.save_custom_gesture(a)
            )
            save_button.pack(side=tk.RIGHT)
            
        # Custom Voice Section
        for action in ['shutdown', 'lock']:
            frame = ttk.Frame(voice_tab)
            frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame, text=f"{action.title()}:").pack(side=tk.LEFT, padx=(0, 10))
            
            # Show saved commands
            if self.custom_voice_commands[action]:
                cmd_text = ", ".join(self.custom_voice_commands[action])
                if len(cmd_text) > 20:
                    cmd_text = cmd_text[:20] + "..."
            else:
                cmd_text = "None saved"
                
            cmd_label = ttk.Label(frame, text=cmd_text)
            cmd_label.pack(side=tk.LEFT, padx=(0, 10))
            
            save_button = ttk.Button(
                frame,
                text=f"Save New",
                command=lambda a=action: self.save_voice_command(a)
            )
            save_button.pack(side=tk.RIGHT)
        
        # Remove the status bar
        # status_bar = ttk.Label(
        #     self.root, 
        #     text="Ready | Gestures and commands saved automatically",
        #     relief=tk.SUNKEN, 
        #     anchor=tk.W
        # )
        # status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def detect_gestures(self):
        cap = cv2.VideoCapture(0)
        mp_draw = mp.solutions.drawing_utils
        
        # Variables for gesture detection timing
        last_detection_time = 0
        detection_cooldown = 10  # Cooldown between detections
        
        # Variables for gesture recognition duration
        gesture_start_time = 0
        current_action = None
        
        try:
            while self.is_detecting and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Add delay to slow down processing
                cv2.waitKey(100)
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                current_time = time.time()
                
                if results.multi_hand_landmarks:
                    landmarks = results.multi_hand_landmarks[0].landmark
                    
                    # Enhanced hand landmarks visualization
                    mp_draw.draw_landmarks(
                        frame, 
                        results.multi_hand_landmarks[0],
                        self.mp_hands.HAND_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0,255,0), thickness=2),
                        mp_draw.DrawingSpec(color=(0,0,255), thickness=2)
                    )
                    
                    # Check if enough time has passed since last detection
                    if current_time - last_detection_time >= detection_cooldown:
                        matched = False
                        for action in self.system_actions.keys():
                            for pattern in self.custom_gestures[action]:
                                if self.match_gesture_pattern(landmarks, pattern):
                                    matched = True
                                    # If this is the first detection of this gesture
                                    if gesture_start_time == 0:
                                        gesture_start_time = current_time
                                        current_action = action
                                    # If the gesture has been held for 1 second and it's the same action
                                    elif current_time - gesture_start_time >= 1.0 and action == current_action:
                                        self.status_label.config(text=f"Custom {action.title()} gesture detected!")
                                        last_detection_time = current_time
                                        # Execute the action immediately
                                        self.system_actions[action]()
                                        return  # Exit after executing the action
                                    break
                        
                        # If no gesture matched, reset the timer
                        if not matched:
                            gesture_start_time = 0
                            current_action = None
                
                cv2.imshow("Gesture Detection", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    # Add this new method for matching custom gestures
    def match_gesture_pattern(self, landmarks, pattern):
        finger_tips = [8, 12, 16, 20]
        finger_bases = [6, 10, 14, 18]
        thumb_tip = 4
        thumb_base = 2
        
        # Check thumb
        thumb_up = landmarks[thumb_tip].y < landmarks[thumb_base].y
        if thumb_up != pattern['thumb']:
            return False
            
        # Check fingers
        current_fingers = [
            landmarks[tip].y < landmarks[base].y 
            for tip, base in zip(finger_tips, finger_bases)
        ]
        
        return current_fingers == pattern['fingers']

    def listen_for_commands(self):
        with sr.Microphone() as source:
            while self.is_listening:
                try:
                    audio = self.speech_recognizer.listen(source, timeout=1)
                    text = self.speech_recognizer.recognize_google(audio).lower()
                    
                    # Check both default and custom commands
                    for action in self.system_actions.keys():
                        if (any(phrase in text for phrase in self.voice_commands[action]) or
                            any(cmd in text for cmd in self.custom_voice_commands[action])):
                            self.confirm_action(action, "voice command")
                            break
                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    continue
                except sr.RequestError:
                    messagebox.showerror("Error", "Could not connect to speech recognition service")
                    self.toggle_voice_recognition()

    def confirm_action(self, action_type, trigger_type):
        # Directly execute the action without showing confirmation popup
        self.system_actions[action_type]()

    def lock_system(self):
        system = platform.system().lower()
        try:
            if system == "windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif system == "linux":
                os.system("loginctl lock-session")
            elif system == "darwin":
                os.system("/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to lock: {str(e)}")

    # Add this method after lock_system method
    def shutdown_system(self):
        system = platform.system().lower()
        try:
            if system == "windows":
                os.system("shutdown /s /t 1")
            elif system == "linux":
                os.system("shutdown -h now")
            elif system == "darwin":  # macOS
                os.system("sudo shutdown -h now")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to shutdown: {str(e)}")

    def run(self):
        self.root.mainloop()

    def toggle_voice_recognition(self):
        if not self.is_listening:
            try:
                # Test microphone access
                with sr.Microphone() as source:
                    self.speech_recognizer.adjust_for_ambient_noise(source, duration=1)
                
                self.is_listening = True
                self.voice_button.config(text="Stop Voice Recognition")
                self.status_label.config(text="Listening for voice commands...")
                threading.Thread(target=self.listen_for_commands, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Microphone error: {str(e)}")
        else:
            self.is_listening = False
            self.voice_button.config(text="Start Voice Recognition")
            self.status_label.config(text="System Ready")

    # Add this method after toggle_voice_recognition
    def toggle_gesture_recognition(self):
        if not self.is_detecting:
            try:
                # Test camera access before starting
                test_cap = cv2.VideoCapture(0)
                if not test_cap.isOpened():
                    messagebox.showerror("Error", "Cannot access webcam")
                    return
                test_cap.release()
                
                self.is_detecting = True
                self.gesture_button.config(text="Stop Gesture Recognition")
                self.status_label.config(text="Detecting hand gestures...")
                threading.Thread(target=self.detect_gestures, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Camera error: {str(e)}")
        else:
            self.is_detecting = False
            self.gesture_button.config(text="Start Gesture Recognition")
            self.status_label.config(text="System Ready")

    def check_gesture(self, landmarks, action_type):
        pattern = self.gesture_patterns[action_type]
        
        # Finger indices
        finger_tips = [8, 12, 16, 20]  # Index, middle, ring, pinky tips
        finger_bases = [6, 10, 14, 18]  # Index, middle, ring, pinky bases
        thumb_tip = 4
        thumb_base = 2

        # Check thumb
        thumb_up = landmarks[thumb_tip].y < landmarks[thumb_base].y
        if thumb_up != pattern['thumb']:
            return False

        # Check other fingers
        for tip, base, should_be_up in zip(finger_tips, finger_bases, pattern['fingers']):
            finger_up = landmarks[tip].y < landmarks[base].y
            if finger_up != should_be_up:
                return False

        return True

    def save_custom_gesture(self, action_type):
        if self.is_detecting:
            messagebox.showinfo("Info", "Please stop gesture detection first")
            return
            
        self.status_label.config(text=f"Ready to save {action_type} gesture...")
        
        cap = cv2.VideoCapture(0)
        mp_draw = mp.solutions.drawing_utils
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                
                if results.multi_hand_landmarks:
                    landmarks = results.multi_hand_landmarks[0].landmark
                    
                    # Draw hand landmarks
                    mp_draw.draw_landmarks(
                        frame, 
                        results.multi_hand_landmarks[0],
                        self.mp_hands.HAND_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(0,255,0), thickness=2),
                        mp_draw.DrawingSpec(color=(0,0,255), thickness=2)
                    )
                    
                    # Show finger status
                    finger_tips = [8, 12, 16, 20]
                    finger_bases = [6, 10, 14, 18]
                    thumb_tip = 4
                    thumb_base = 2
                    
                    thumb_up = landmarks[thumb_tip].y < landmarks[thumb_base].y
                    fingers = [landmarks[tip].y < landmarks[base].y 
                             for tip, base in zip(finger_tips, finger_bases)]
                    
                    # Display finger status
                    status_text = f"Thumb: {'Up' if thumb_up else 'Down'}"
                    cv2.putText(frame, status_text, (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    for i, is_up in enumerate(fingers):
                        finger_name = ['Index', 'Middle', 'Ring', 'Pinky'][i]
                        status = 'Up' if is_up else 'Down'
                        cv2.putText(frame, f"{finger_name}: {status}", 
                                  (10, 90 + i*30), cv2.FONT_HERSHEY_SIMPLEX, 
                                  0.6, (0, 255, 0), 2)
                    
                cv2.putText(frame, f"Hold gesture for {action_type} and press 'S' to save", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("Save Custom Gesture", frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('s') and results and results.multi_hand_landmarks:
                    self.custom_gestures[action_type].append({
                        'thumb': thumb_up,
                        'fingers': fingers
                    })
                    # Save to file
                    self.save_data(self.gestures_file, self.custom_gestures)
                    messagebox.showinfo("Success", f"New gesture saved for {action_type}!")
                    break
                elif key == 27:  # ESC
                    break
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.status_label.config(text="System Ready")
            # Refresh the UI
            self.setup_gui()

    def save_voice_command(self, action_type):
        if self.is_listening:
            messagebox.showinfo("Info", "Please stop voice recognition first")
            return
            
        self.status_label.config(text=f"Ready to save {action_type} command...")
        
        try:
            with sr.Microphone() as source:
                messagebox.showinfo("Record Command", 
                    f"Click OK and speak your custom command for {action_type}")
                
                self.speech_recognizer.adjust_for_ambient_noise(source)
                audio = self.speech_recognizer.listen(source, timeout=5)
                text = self.speech_recognizer.recognize_google(audio).lower()
                
                self.custom_voice_commands[action_type].append(text)
                # Save to file
                self.save_data(self.voice_file, self.custom_voice_commands)
                messagebox.showinfo("Success", 
                    f"New voice command '{text}' saved for {action_type}!")
                
        except sr.RequestError:
            messagebox.showerror("Error", "Could not connect to speech recognition service")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save command: {str(e)}")
        finally:
            self.status_label.config(text="System Ready")
            # Refresh the UI
            self.setup_gui()

if __name__ == "__main__":
    app = ShutdownController()
    app.run()