function H(url, ...x) {
    $.post({
      url: url,
      success: function(data) {
        $("#counter").html(data)
        return false
      }
    })
}
