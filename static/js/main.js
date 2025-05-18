// örnek: index.html yüklendiğinde
fetch("/api/polls")
  .then(res => res.json())
  .then(ids => {
    // sayfaya <ul><li><a href="poll.html?id=…">Anket …</a></li>…</ul> ekle
  });
