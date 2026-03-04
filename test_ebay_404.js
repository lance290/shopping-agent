const url = "https://buy-anything.com/api/out?url=https%3A%2F%2Fwww.ebay.com%2Fitm%2F287165648886%3F_skw%3Dlawn%2Bmower%26hash%3Ditem42dc680ff6%3Ag%3ANVEAAeSwIj9pn-pR%26amdata%3Denc%253AAQALAAAA8ACCtXRWQnOEpyOqnQQ8KGbs5un2pJgnMwel9zp8vNviqAn90FZ8DH4hAscTErMgxubntxuv%252BPZDW7cbh8V%252BKx4ZOZEXBpZjcNGG%252FdGenx%252BdF1tx5IIWn%252BguxWbciju%252BT3K52AtEfsy7CnDV%252Fmze0syUQvt0V00uNO9kJt%252B2nVJkSg6PKQA2K88N4c3iZ%252FiPK7dx%252F4AewElcDzImyNJI8NJFal5C1WoHqXG0AhO%252FUl7BXwHHEYHYECR23%252FFHAjl93Yn5LusEzSi0PyIXVxDxiiSgoCEFPcoStblnM5rgMJWOV4kHoq5WJ8nI1UzgCMJ75w%253D%253D"

fetch(url, { redirect: 'manual' })
  .then(res => {
    console.log(res.status, res.statusText);
    return res.text();
  })
  .then(text => console.log(text.slice(0, 200)))
  .catch(err => console.error(err));
