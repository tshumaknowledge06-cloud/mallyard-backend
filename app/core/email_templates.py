def password_reset_email(reset_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Password Reset</title>
</head>

<body style="
margin:0;
padding:0;
background:#F8F7F2;
font-family:Arial,sans-serif;
">

<table width="100%" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="padding:40px 20px;">

<table
width="600"
style="
background:white;
border-radius:16px;
padding:40px;
box-shadow:0 4px 18px rgba(0,0,0,.08);
">

<tr>
<td align="center">

<h1 style="
color:#046D56;
margin-bottom:8px;
">
The Mallyard
</h1>

<p style="
color:#666;
font-size:16px;
margin-bottom:30px;
">
Find. Compare. Connect.
</p>

<h2 style="color:#1A1A1A;">
Reset Your Password
</h2>

<p style="
color:#555;
line-height:1.6;
font-size:15px;
">
We received a request to reset the password for your
The Mallyard account.
</p>

<p style="
color:#555;
line-height:1.6;
font-size:15px;
">
Click the button below to create a new password.
</p>

<p style="margin:40px 0;">

<a
href="{reset_url}"
style="
background:#046D56;
color:white;
padding:16px 34px;
border-radius:8px;
text-decoration:none;
font-weight:bold;
display:inline-block;
">
Reset Password
</a>

</p>

<p style="
font-size:13px;
color:#777;
line-height:1.6;
">
This link expires in
<strong>30 minutes</strong>.
</p>

<p style="
font-size:13px;
color:#777;
line-height:1.6;
">
If you didn't request this password reset,
you can safely ignore this email.
</p>

<hr style="
margin:30px 0;
border:none;
border-top:1px solid #EEE;
">

<p style="
font-size:12px;
color:#999;
">

Need help?

Reply to this email or visit
<strong>themallyard.com</strong>

</p>

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""