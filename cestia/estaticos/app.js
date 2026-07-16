(() => {
  const input = document.getElementById("q");
  if (!input) return;
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      input.value = "";
      input.blur();
    }
  });
})();
