"""Static continue page. The token stays in the fragment and is not rendered."""

CONTINUE_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Continue</title></head>
<body>
<p>Continuing.</p>
<script>
(function () {
  var params = new URLSearchParams(window.location.search);
  var raw = window.location.hash.charAt(0) === "#" ? window.location.hash.slice(1) : "";
  history.replaceState(null, "", window.location.pathname);
  if (params.has("token")) {
    return;
  }
  if (!raw) {
    return;
  }
  fetch("/api/auth/session", {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({token: raw})
  });
})();
</script>
</body>
</html>
"""
