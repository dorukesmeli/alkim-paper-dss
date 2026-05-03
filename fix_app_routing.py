import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

# Add main function and routing at the bottom
main_code = """
# ===========================================================================
# MAIN ROUTING
# ===========================================================================
def main():
    st.write("APP LOADED") # Temporary debug line
    
    # Check default page
    if "active_page" not in st.session_state:
        st.session_state.active_page = "home"
        
    page = st.session_state.active_page
    
    # Routing logic
    if page == "home":
        page_home()
    elif page == "orders":
        page_orders()
    elif page == "settings":
        page_settings()
    elif page == "results":
        page_results()
    else:
        st.session_state.active_page = "home"
        page_home()

if __name__ == "__main__":
    main()
"""

# Only append if it's not already there
if "def main():" not in content:
    content += "\n" + main_code

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)

print("Main routing appended")
