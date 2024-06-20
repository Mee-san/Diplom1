function toggleContextMenu(event) {
  const menu = document.getElementById('contextMenu');
  if (menu.style.display === 'block') {
      menu.style.display = 'none';
  } else {
      const rect = event.target.getBoundingClientRect();
      menu.style.display = 'block';
      menu.style.top = `${rect.bottom}px`;
      menu.style.left = `${rect.left}px`;
  }
}

