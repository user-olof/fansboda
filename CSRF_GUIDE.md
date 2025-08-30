# CSRF Protection Guide for Flask Application

## 🔐 CSRF Token in LoginForm - Complete Guide

Your `LoginForm` already has CSRF protection built-in! Here's everything you need to know:

## How CSRF Protection Works in Your App

### 1. **Automatic CSRF Token Inclusion**
```python
# forms.py - Your LoginForm already has CSRF protection
from flask_wtf import FlaskForm  # This automatically includes CSRF protection

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")
    # csrf_token is automatically included - no need to add it manually!
```

### 2. **App Configuration**
```python
# app.py - CSRF protection is now enabled
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"  # Required for CSRF
csrf = CSRFProtect(app)  # This enables CSRF protection app-wide
```

### 3. **Template Usage**
```html
<!-- templates/login.html - CSRF token is automatically included -->
<form action="" method="post" novalidate>
    {{ form.hidden_tag() }}  <!-- This includes the CSRF token automatically -->
    
    <!-- Your form fields -->
    {{ form.username.label }}
    {{ form.username(size=32) }}
    
    {{ form.password.label }}
    {{ form.password(size=32) }}
    
    {{ form.remember_me() }} {{ form.remember_me.label }}
    {{ form.submit() }}
</form>
```

## Manual CSRF Token Access (if needed)

### **In Templates:**
```html
<!-- If you need to access the CSRF token manually -->
<form method="post">
    <!-- Method 1: Using form.hidden_tag() (recommended) -->
    {{ form.hidden_tag() }}
    
    <!-- Method 2: Manual CSRF token (not usually needed) -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    
    <!-- Method 3: Access via form field -->
    <input type="hidden" name="csrf_token" value="{{ form.csrf_token.current_token }}"/>
    
    <!-- Your other form fields -->
</form>
```

### **In Python Code:**
```python
from forms import LoginForm

# Creating a form automatically generates CSRF token
form = LoginForm()

# Access the CSRF token
csrf_token = form.csrf_token.current_token
# or
csrf_token = form.csrf_token._value()

# The token is also available in templates via csrf_token() function
```

### **In JavaScript (AJAX requests):**
```html
<!-- In your template, make CSRF token available to JavaScript -->
<script>
    window.csrf_token = "{{ csrf_token() }}";
</script>

<script>
    // Use in AJAX requests
    fetch('/api/endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrf_token
        },
        body: JSON.stringify(data)
    });
</script>
```

## Testing with CSRF Tokens

### **Regular Tests (CSRF Disabled)**
```python
# tests/conftest.py - CSRF disabled for easier testing
@pytest.fixture
def client():
    app.config["WTF_CSRF_ENABLED"] = False  # Disable for testing
    # ... rest of configuration
```

### **CSRF-Enabled Tests**
```python
# tests/conftest.py - CSRF enabled for specific tests
@pytest.fixture
def client_with_csrf():
    app.config["WTF_CSRF_ENABLED"] = True  # Enable for CSRF testing
    # ... rest of configuration

# tests/test_forms.py - Testing with CSRF
def test_csrf_token_present(client_with_csrf):
    with client_with_csrf.application.app_context():
        form = LoginForm()
        csrf_token = form.csrf_token._value()
        assert csrf_token is not None
```

### **Testing Form Submission with CSRF**
```python
def test_login_with_csrf(client_with_csrf):
    # First, get the login page to get a CSRF token
    response = client_with_csrf.get('/login')
    
    # Extract CSRF token from response (in real tests, you might parse HTML)
    # For testing, you can also create a form and get the token
    with client_with_csrf.application.app_context():
        form = LoginForm()
        csrf_token = form.csrf_token._value()
    
    # Submit form with CSRF token
    response = client_with_csrf.post('/login', data={
        'username': 'testuser',
        'password': 'testpass',
        'csrf_token': csrf_token
    })
```

## CSRF Configuration Options

```python
# app.py - Advanced CSRF configuration
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Optional configurations
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit
app.config['WTF_CSRF_SSL_STRICT'] = True  # Require HTTPS in production
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']  # Custom headers
```

## Error Handling

```python
# Handle CSRF errors
from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', reason=e.description), 400
```

## Common Issues and Solutions

### **Issue 1: CSRF Token Missing**
```
ValidationError: CSRF token missing
```
**Solution:** Ensure `{{ form.hidden_tag() }}` is in your template.

### **Issue 2: CSRF Token Expired**
```
ValidationError: CSRF token expired
```
**Solution:** Set `WTF_CSRF_TIME_LIMIT = None` or increase the time limit.

### **Issue 3: CSRF Token Invalid**
```
ValidationError: CSRF token invalid
```
**Solution:** Check that your SECRET_KEY is set and consistent.

## Production Considerations

1. **Use a strong SECRET_KEY**:
   ```python
   import secrets
   app.config['SECRET_KEY'] = secrets.token_hex(32)
   ```

2. **Enable SSL strict mode in production**:
   ```python
   app.config['WTF_CSRF_SSL_STRICT'] = True
   ```

3. **Set appropriate time limits**:
   ```python
   app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
   ```

## Summary

✅ **Your LoginForm already has CSRF protection** - no manual addition needed!  
✅ **CSRF token is automatically included** via `form.hidden_tag()`  
✅ **App is configured with CSRFProtect**  
✅ **Tests are set up to handle CSRF properly**  

Your CSRF implementation is complete and secure! 🎉