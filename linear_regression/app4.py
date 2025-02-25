from flask import Flask, request, jsonify, session, render_template  # type: ignore
from flask_cors import CORS  # type: ignore
import pickle
import numpy as np  # type: ignore
import re  # For regex validation of input format

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "1204"  # Required for session handling
CORS(app)

# Load trained Linear Regression model
with open("house_price_model.pkl", "rb") as f:
    model = pickle.load(f)

# Home route (Landing page)
@app.route('/')
def home():
    return render_template("index.html")

# Serve Chatbot Page
@app.route('/chatbot', methods=['GET'])
def chatbot_page():
    return render_template("chatbot2.html")  # Serve chatbot UI

# Chatbot logic
@app.route('/chatbot', methods=['POST'])
def chatbot():
    if "user_data" not in session:
        session["user_data"] = {}

    user_data = session["user_data"]
    user_input = request.json.get("message", "").strip().lower()

    # Starting message
    if "hi" in user_input or "hello" in user_input or "start" in user_input:
        session["user_data"] = {}
        return jsonify({"response": "Hi! I will help you predict your house price based on square area, number of bedrooms, and number of bathrooms. Let's get started! How many people are in your family?"})

    # Step 1: Get Family Size
    if "FamilySize" not in user_data:
        try:
            user_data["FamilySize"] = int(user_input)
            session["user_data"] = user_data
            return jsonify({"response": "How often do you have guests? (Rarely/Frequently)"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for family size."})

    # Step 2: Get Guest Frequency
    if "GuestFrequency" not in user_data:
        if user_input in ["rarely", "frequently"]:
            user_data["GuestFrequency"] = user_input
            session["user_data"] = user_data
            return jsonify({"response": "Do you have elderly members in your family? (Yes/No)"})
        return jsonify({"response": "❌ Please answer 'Rarely' or 'Frequently'."})

    # Step 3: Elderly Members
    if "ElderlyMembers" not in user_data:
        if user_input in ["yes", "no"]:
            user_data["ElderlyMembers"] = user_input
            session["user_data"] = user_data
            return jsonify({"response": "Would you like a basement? (Yes/No)"})
        return jsonify({"response": "❌ Please answer 'Yes' or 'No'."})

    # Step 4: Basement Preference
    if "Basement" not in user_data:
        if user_input in ["yes", "no"]:
            user_data["Basement"] = user_input
            session["user_data"] = user_data

            if user_input == "no":
                # Set default values for basement bathrooms if there's no basement
                user_data["BsmtFullBath"] = 0
                user_data["BsmtHalfBath"] = 0
                session["user_data"] = user_data
                return jsonify({"response": "Enter your living area in Width x Length format (e.g., 30x50):"})

            if user_data["GuestFrequency"] == "frequently":
                # If guests come frequently, suggest that full bathroom is not needed
                user_data["BsmtFullBath"] = 0  # Set default value
                session["user_data"] = user_data
                return jsonify({"response": "Since you have frequent guests, a full basement bathroom is not required. How many half bathrooms do you need in the basement?"})
            
            return jsonify({"response": "How many full bathrooms do you need in the basement?"})

        return jsonify({"response": "❌ Please answer 'Yes' or 'No'."})

    # Step 5: Basement Full Bathrooms (Only ask if guests are not frequent)
    if "BsmtFullBath" not in user_data and user_data["Basement"] == "yes":
        try:
            user_data["BsmtFullBath"] = int(user_input)
            session["user_data"] = user_data
            return jsonify({"response": "How many half bathrooms do you need in the basement?"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for basement full bathrooms."})

    # Step 6: Basement Half Bathrooms
    if "BsmtHalfBath" not in user_data and user_data["Basement"] == "yes":
        try:
            user_data["BsmtHalfBath"] = int(user_input)
            session["user_data"] = user_data
            return jsonify({"response": "Enter your living area in Width x Length format (e.g., 30x50):"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for basement half bathrooms."})

    # Step 7: Get Living Area
    if "GrLivArea" not in user_data:
        match = re.match(r"(\d+)x(\d+)", user_input)
        if match:
            width, length = map(int, match.groups())
            user_data["GrLivArea"] = width * length
            session["user_data"] = user_data
            return jsonify({"response": "How many bedrooms above ground do you need?"})
        return jsonify({"response": "❌ Please enter the area in Width x Length format (e.g., 30x50)."})

    # Step 8: Get Bedrooms Above Ground
    if "BedroomAbvGr" not in user_data:
        try:
            bedrooms = int(user_input)

            # If elderly members are present, suggest at least 2 bedrooms
            if user_data["ElderlyMembers"] == "yes" and bedrooms < 2:
                return jsonify({"response": "Since you have elderly members, it is recommended to have at least 2 bedrooms. How many bedrooms do you need?"})

            user_data["BedroomAbvGr"] = bedrooms
            session["user_data"] = user_data
            return jsonify({"response": "How many full bathrooms do you need above ground?"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for bedrooms."})

    # Step 9: Get Full Bathrooms
    if "FullBath" not in user_data:
        try:
            full_bathrooms = int(user_input)

            # If elderly members are present, suggest at least 1 full bathroom
            if user_data["ElderlyMembers"] == "yes" and full_bathrooms < 1:
                return jsonify({"response": "Since you have elderly members, it is recommended to have at least 1 full bathroom. How many full bathrooms do you need?"})

            user_data["FullBath"] = full_bathrooms
            session["user_data"] = user_data
            return jsonify({"response": "How many half bathrooms do you need above ground?"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for full bathrooms."})

    # Step 10: Get Half Bathrooms Above Ground
    if "HalfBath" not in user_data:
        try:
            user_data["HalfBath"] = int(user_input)

            # Predict house price
            features = np.array([[user_data["GrLivArea"], user_data["BedroomAbvGr"],
                                  user_data["FullBath"], user_data["BsmtFullBath"],
                                  user_data["BsmtHalfBath"], user_data["HalfBath"]]])
            predicted_price = model.predict(features)[0]
            user_data["predicted_price"] = predicted_price
            session["user_data"] = user_data

            return jsonify({"response": f"🏠 The estimated house price is **${predicted_price:,.2f}**. Are you interested? (Yes/No)"})
        except ValueError:
            return jsonify({"response": "❌ Please enter a valid number for half bathrooms."})
     # User says "No" to the predicted price
    if "interested" not in user_data:
        if "yes" in user_input:
            return jsonify({"response": "🎉 Great! Let's proceed with the next steps for purchasing. Click here to continue: [Proceed to Purchase](https://dummy-link.com)"})

        
        
        elif "no" in user_input:
            return jsonify({"response": "Let's adjust your preferences. How many bedrooms do you need?"})

    # 🔥 Fix: Directly update the bedroom count instead of checking if it exists
    try:
        new_bedrooms = int(user_input)  # Convert input to an integer
        user_data["BedroomAbvGr"] = new_bedrooms  # Overwrite the old bedroom count
        session["user_data"] = user_data  # Save the updated data

        # 🔄 **Recalculate house price**
        features = np.array([[user_data["GrLivArea"], user_data["BedroomAbvGr"],
                            user_data["FullBath"], user_data["BsmtFullBath"],
                            user_data["BsmtHalfBath"], user_data["HalfBath"]]])
        predicted_price = model.predict(features)[0]  # Get new price prediction
        user_data["predicted_price"] = predicted_price
        session["user_data"] = user_data  # Save new price in session

        return jsonify({"response": f"🏠 The new estimated house price is **${predicted_price:,.2f}**. Are you interested? (Yes/No)"})

    except ValueError:
        return jsonify({"response": "❌ Please enter a valid number for bedrooms."})


    

# Run Flask server
if __name__ == '__main__':
    app.run(debug=True)
