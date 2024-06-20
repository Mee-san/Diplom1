// genre-menu.js
function toggleGenreMenu(event) {
  const menu = document.getElementById('genreMenu');
  if (menu.style.display === 'block') {
      menu.style.display = 'none';
  } else {
      const rect = event.target.getBoundingClientRect();
      menu.style.display = 'block';
      menu.style.top = `${rect.bottom}px`;
      menu.style.left = `${rect.left}px`;
  }
}
