import markdown

# Store the D&D CSS content
# From: https://github.com/fatters/dnd-css/blob/master/dist/dnd.min.css
# This will be imported and used in main_window.py now
DND_CSS = """
@import "https://fonts.googleapis.com/css?family=Libre+Baskerville&display=swap";

/* Apply parchment background ONLY to the body inside the QTextBrowser */
body {
    /* background: #fdf9ec; /* REMOVED - Handled by widget palette */ */
    font-family: 'Libre Baskerville', serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-size: 16px;
    color: black; /* Ensure default text color is dark on light background */
    padding: 10px; /* Add some padding around the content */
}
h1,h2,h3,h4,h5,h6 {
    color:#7a2b17 !important; /* Original D&D Red, try forcing it */
    /* color: #00FF00; /* TEST: Bright Green */ */
    text-transform:uppercase !important; /* Force uppercase too */
    line-height:1.1;
    margin:24px 0 12px;
    font-family: 'Libre Baskerville', serif; /* Ensure headers use the font too */
}
h1:first-letter,h2:first-letter,h3:first-letter,h4:first-letter,h5:first-letter,h6:first-letter {
    font-size:150%;
}
h1 {
    font-size:24px;
    border-bottom:2px solid tan !important;
}
h2 {
    border-bottom:2px solid tan !important;
}
p {
    line-height:1.4;
    margin:0 0 1em 0; /* Add some bottom margin */
    color: black; 
}
p+p {
    text-indent:24px;
    margin-top:0!important;
}
.box { /* Not used yet, kept for potential */
    background-color:#fff;
    padding:16px;
    border-left:2px solid #000;
    border-right:2px solid #000;
    overflow:hidden;
    margin:16px 0
}
/* Basic styles for tables */
table {
    border-collapse: collapse;
    margin: 1em 0;
    width: 95%; 
    border: 1px solid tan !important;
    background-color: #fdf0d8 !important; /* Slightly darker parchment for tables */
}
th, td {
    border: 1px solid tan !important;
    padding: 0.5em;
    text-align: left;
    color: black !important; /* Ensure table text is dark */
}
th {
    background-color: #e1c699 !important; 
    color: #7a2b17 !important;
    font-weight: bold;
}
/* Basic styles for code blocks and inline code */
pre {
    background-color: #eee !important;
    border: 1px solid #ccc !important;
    padding: 10px;
    margin: 1em 0;
    overflow: auto;
    font-family: monospace;
    white-space: pre-wrap; 
    word-wrap: break-word; 
    color: black !important; /* Ensure code text is dark */
}
code {
    font-family: monospace;
    background-color: #eee !important;
    padding: 0.1em 0.3em;
    border-radius: 3px;
    color: black !important; /* Ensure inline code text is dark */
}
pre > code { 
    background-color: transparent !important;
    padding: 0;
    border-radius: 0;
}
/* Basic styles for blockquotes */
blockquote {
    border-left: 4px solid #7a2b17 !important;
    margin: 1em 0 1em 20px;
    padding: 0.5em 10px;
    color: #333 !important; /* Darker grey for quote text */
    background-color: #fdf0d8 !important; /* Slightly darker parchment */
}
blockquote p {
    margin-bottom: 0; 
    color: #333 !important; /* Ensure quote paragraph text is dark */
}
hr {
    border: none !important;
    border-top: 1px solid #7a2b17 !important;
    margin: 1.5em 0;
}
a {
  color: #58180D !important; /* Darker red for links */
  text-decoration: underline !important;
}
a:visited {
   color: #40110A !important;
}

/* --- Stat Block Styles --- */
.stat-block {
    background-color: #fdf0d8 !important; /* Slightly darker parchment */
    border: 1px solid #7a2b17 !important; /* D&D red border */
    padding: 10px !important;
    margin: 1em 0 !important;
    font-family: sans-serif !important; /* Use a cleaner sans-serif for stats */
    color: black !important;
}
.stat-block-title {
    font-weight: bold !important;
    font-size: 1.1em !important;
    color: #7a2b17 !important;
    border-bottom: 1px solid #7a2b17 !important;
    margin-bottom: 5px !important;
    padding-bottom: 3px !important;
}
.stat-block-property {
    font-weight: bold !important;
    color: #58180D !important; /* Darker red */
}
.stat-block-line {
    margin-bottom: 3px !important;
}

"""

def markdown_to_html_fragment(md_text: str) -> str:
    """Converts a Markdown string to an HTML fragment (no <html> tags)."""
    try:
        # Convert markdown to HTML fragment
        # Added extensions: 'tables', 'fenced_code', 'attr_list', 'md_in_html'
        html_fragment = markdown.markdown(
            md_text, 
            extensions=['tables', 'fenced_code', 'attr_list', 'md_in_html']
        )
        return html_fragment
    except Exception as e:
        print(f"Error converting Markdown: {e}") 
        # Return an error message as a simple HTML fragment
        return f"<p><b>Error rendering Markdown:</b> {e}</p><pre>{md_text}</pre>" 