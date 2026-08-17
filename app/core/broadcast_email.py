from html import escape


def build_broadcast_email(
    subject: str,
    message: str,
) -> str:

    safe_subject = escape(subject)
    safe_message = escape(message).replace("\n", "<br>")

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>{safe_subject}</title>
</head>

<body style="
    margin:0;
    padding:0;
    background:#F8F7F2;
    font-family:Arial, Helvetica, sans-serif;
">

    <table
        width="100%"
        cellpadding="0"
        cellspacing="0"
        style="background:#F8F7F2; padding:40px 15px;"
    >
        <tr>
            <td align="center">

                <table
                    width="100%"
                    cellpadding="0"
                    cellspacing="0"
                    style="
                        max-width:600px;
                        background:#FFFFFF;
                        border-radius:16px;
                        overflow:hidden;
                        box-shadow:0 8px 30px rgba(0,0,0,0.06);
                    "
                >

                    <!-- HEADER -->

                    <tr>
                        <td style="
                            background:#046D56;
                            padding:28px 32px;
                            text-align:center;
                        ">

                            <div style="
                                color:#D4AF37;
                                font-size:26px;
                                font-weight:bold;
                                letter-spacing:1px;
                            ">
                                THE MALLYARD
                            </div>

                            <div style="
                                color:#F9F7F3;
                                font-size:12px;
                                margin-top:6px;
                                letter-spacing:1.5px;
                            ">
                                FIND. COMPARE. CONNECT.
                            </div>

                        </td>
                    </tr>


                    <!-- CONTENT -->

                    <tr>
                        <td style="padding:40px 35px;">

                            <h1 style="
                                margin:0 0 22px 0;
                                color:#1A1A1A;
                                font-size:24px;
                                line-height:1.3;
                            ">
                                {safe_subject}
                            </h1>

                            <div style="
                                color:#444444;
                                font-size:16px;
                                line-height:1.8;
                            ">
                                {safe_message}
                            </div>

                            <div style="
                                margin-top:35px;
                                padding-top:25px;
                                border-top:1px solid #E8E5DD;
                            ">

                                <p style="
                                    margin:0;
                                    color:#046D56;
                                    font-weight:bold;
                                    font-size:15px;
                                ">
                                    Growing African commerce, together.
                                </p>

                            </div>

                        </td>
                    </tr>


                    <!-- FOOTER -->

                    <tr>
                        <td style="
                            background:#1A1A1A;
                            padding:25px 30px;
                            text-align:center;
                        ">

                            <div style="
                                color:#F9F7F3;
                                font-size:13px;
                            ">
                                The Mallyard
                            </div>

                            <div style="
                                color:#A9A9A9;
                                font-size:11px;
                                margin-top:8px;
                            ">
                                Find. Compare. Connect.
                            </div>

                            <div style="
                                color:#777777;
                                font-size:10px;
                                margin-top:14px;
                            ">
                                © MALLYARD ENTERPRISES (PRIVATE) LIMITED
                            </div>

                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

</body>
</html>
"""