document.addEventListener("DOMContentLoaded", function() {
    var button = document.getElementById("createPostButton");
    var menu = document.getElementById("contextMenu");

    button.addEventListener("click", function() {
        menu.style.display = "block";
    });

    document.addEventListener("click", function(event) {
        if (!menu.contains(event.target) && event.target !== button) {
            menu.style.display = "none";
        }
    });
});
