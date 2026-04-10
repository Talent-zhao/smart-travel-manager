(function ($) {
    $.getCookie = function (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    $('#book-collect').click(function () {
        // 点击收藏
        var csrftoken = $.getCookie('csrftoken');
        var book_id = $("[name='book_id']").val();
        var last_url = document.getElementsByName("book_id")[0].getAttribute('last_url');

        $.ajax({
            url: window.__user_path_prefix__ + '/collect/' + book_id + '/',
            type: 'POST',
            data: {'book_id': book_id, 'from': 'shop'},

            success: function (res) {
                if (res.code === 1) {
                    $("#book-collect span svg").css('color', '#FFD661');
                    $("#book-collect").children("span").last().text('已收藏');
                    var collect_num = parseInt($("#book_act_count").children("span").eq(2).children('strong').last().text())
                    $("#book_act_count").children("span").eq(2).children('strong').last().text(collect_num + 1)
                } else if (res.code === 2) {
                    $("#book-collect span svg").css("color", '');
                    $("#book-collect").children("span").last().text('收藏')
                    var collect_num = parseInt($("#book_act_count").children("span").eq(2).children('strong').last().text())
                    $("#book_act_count").children("span").eq(2).children('strong').last().text(collect_num - 1)

                } else if (res.code === 3) {
                    let params = JSON.stringify({'book_id': book_id});
                    window.location.href = window.__user_path_prefix__ + '/login/?last_url=' + last_url + '&params=' + params;
                }
            },
            error: function (e) {
                if (e.statusText === 'Forbidden') {
                    let params = JSON.stringify({'book_id': book_id});
                    window.location.href = window.__user_path_prefix__ + '/login/?last_url=' + last_url + '&params=' + params;
                } else {
                    alert(e.statusText)
                }
            },
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        });
    });

    $('#book-take-now').click(function () {
        // 购买(立即取走)
        var csrftoken = $.getCookie('csrftoken');
        var book_id = $("[name='book_id']").val();
        var purchase_num = $("[name='purchase_num']").val();
        var last_url = document.getElementsByName("book_id")[0].getAttribute('last_url');
        $.ajax({
            url: window.__user_path_prefix__ + '/book_take_now/',
            type: 'POST',
            data: {'book_id': book_id, 'purchase_num': purchase_num},

            success: function (res) {
                window.location.href = window.__user_path_prefix__ + '/add_shop_list/?way=take'  + '&book_id=' + res.book_id;
            },
            error: function (e) {
                if (e.statusText === 'Forbidden') {
                    let params = JSON.stringify({'book_id': book_id, 'purchase_num': purchase_num});
                    window.location.href = window.__user_path_prefix__ + '/login/?last_url=' + last_url + '&params=' + params;
                } else {
                    alert(e.statusText)
                }
            },
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        });
    });

    $('#add-shoplist').click(function () {
        // 添加到购物车
        var csrftoken = $.getCookie('csrftoken');
        var book_id = $("[name='book_id']").val();
        var purchase_num = $("[name='purchase_num']").val();
        var last_url = document.getElementsByName("book_id")[0].getAttribute('last_url');
        $.ajax({
            url: window.__user_path_prefix__ + '/add_shop_list/',
            type: 'POST',
            data: {'book_id': book_id, 'purchase_num': purchase_num},

            success: function (res) {
                window.location.href = window.__user_path_prefix__ + '/add_shop_list/?way=add' + '&book_id=' + res.book_id;
            },
            error: function (e) {
                if (e.statusText === 'Forbidden') {
                    let params = JSON.stringify({'book_id': book_id, 'purchase_num': purchase_num});
                    window.location.href = window.__user_path_prefix__ + '/login/?last_url=' + last_url + '&params=' + params;
                } else {
                    alert(e.statusText);
                }
            },
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        });
    });

})(jQuery)