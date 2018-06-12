// patch for string.trim():

if (! String.prototype.trim) {
    String.prototype.trim = function() {
        return this.replace(/^\s+|\s+$/g, '');
    };
}

if (! Number.prototype.toDateTime) {
    var replaces = {
        'yyyy': function(dt) {
            return dt.getFullYear().toString();
        },
        'yy': function(dt) {
            return (dt.getFullYear() % 100).toString();
        },
        'MM': function(dt) {
            var m = dt.getMonth() + 1;
            return m < 10 ? '0' + m : m.toString();
        },
        'M': function(dt) {
            var m = dt.getMonth() + 1;
            return m.toString();
        },
        'dd': function(dt) {
            var d = dt.getDate();
            return d < 10 ? '0' + d : d.toString();
        },
        'd': function(dt) {
            var d = dt.getDate();
            return d.toString();
        },
        'hh': function(dt) {
            var h = dt.getHours();
            return h < 10 ? '0' + h : h.toString();
        },
        'h': function(dt) {
            var h = dt.getHours();
            return h.toString();
        },
        'mm': function(dt) {
            var m = dt.getMinutes();
            return m < 10 ? '0' + m : m.toString();
        },
        'm': function(dt) {
            var m = dt.getMinutes();
            return m.toString();
        },
        'ss': function(dt) {
            var s = dt.getSeconds();
            return s < 10 ? '0' + s : s.toString();
        },
        's': function(dt) {
            var s = dt.getSeconds();
            return s.toString();
        },
        'a': function(dt) {
            var h = dt.getHours();
            return h < 12 ? 'AM' : 'PM';
        }
    };
    var token = /([a-zA-Z]+)/;
    Number.prototype.toDateTime = function(format) {
        var fmt = format || 'yyyy-MM-dd hh:mm:ss'
        var dt = new Date(this * 1000);
        var arr = fmt.split(token);
        for (var i=0; i<arr.length; i++) {
            var s = arr[i];
            if (s && s in replaces) {
                arr[i] = replaces[s](dt);
            }
        }
        return arr.join('');
    };
}

function refresh() {
    var
        t = new Date().getTime(),
        url = location.pathname;
    if (location.search) {
        url = url + location.search + '&t=' + t;
    }
    else {
        url = url + '?t=' + t;
    }
    location.assign(url);
}

/* extend $('textarea').val() 方案来自官网*/

$(function() {
    $.valHooks.textarea = {
      get: function( elem ) {
        return elem.value.replace( /\r?\n/g, "\r\n" );
      }
    };
});

// extends jQuery.form:

$(function () {
    console.log('Extends $form...');
    $.fn.extend({
        showFormError: function (err) {
        /* Params:
        * Should be a dict : {'error': , 'data': , 'message': }, 'data' must be a html tag attribute 'id'.
        * The dict is the common data structure also used by backend APIError.
        * Or should be a string.
        * Description:
        * A jQuery extension. If has error, set error message in the html tag,
        * show the tag with $alert, and make the field be set with '.alert-danger'.
        */
            return this.each(function () {
                var $form = $(this);
                var $alert = $form && $form.find('div.alert-danger');
                var fieldName = err && err.data;
                if (! $form.is('form')) {
                    console.error('Cannot call showFormError() on non-form object.');
                    return;
                }
                $form.find('input').removeClass('alert-danger');
                $form.find('select').removeClass('alert-danger');
                $form.find('textarea').removeClass('alert-danger');
                if ($alert.length === 0) {
                    console.warn('Cannot find .alert-danger element.');
                    return;
                }
                if (err) {
                    /* set error message in the html tag, show the tag with $alert */
                    $alert.text(err.message ? err.message : (err.error ? err.error : err)).removeClass('invisible');

                    /* make the field be set with .alert-danger */
                    if (fieldName) {
                        $form.find('#'+fieldName).addClass('alert-danger');
                    }
                }
                else {
                    $alert.addClass('invisible');
                    $form.find('input').removeClass('alert-danger');
                    $form.find('select').removeClass('alert-danger');
                    $form.find('textarea').removeClass('alert-danger');
                }
            });
        },
        showFormLoading: function (isLoading) {
        /* While waiting data transfer with backend, set button disabled*/
            return this.each(function () {
                var $form = $(this);
                var $submit = $form && $form.find('button[type=submit]');
                var $buttons = $form && $form.find('button');

                if (! $form.is('form')) {
                    console.error('Cannot call showFormLoading() on non-form object.');
                    return;
                }

                if (isLoading) {
                    $buttons.attr('disabled', 'disabled');
                }
                else {
                    $buttons.removeAttr('disabled');
                }
            });
        },
        postJSON: function (url, data, callback) {
        /* only used for form */
            if (arguments.length===2) {
                callback = data;
                data = {};
            }
            return this.each(function () {
                var $form = $(this);
                $form.showFormError();
                $form.showFormLoading(true);//while waiting, set button disabled and
                _httpJSON('POST', url, data, function (err, r) {
                    if (err) {
                        $form.showFormError(err);
                        $form.showFormLoading(false);
                    }
                    callback && callback(err, r);
                });
            });
        }
    });
});

// ajax submit form:

function _httpJSON(method, url, data, callback) {
    var opt = {
        type: method,
        dataType: 'json'
    };
    if (method==='GET') {
        opt.url = url + '?' + data;
    }
    if (method==='POST') {
        opt.url = url;
        opt.data = JSON.stringify(data || {});
        opt.contentType = 'application/json';
    }
    $.ajax(opt).done(function (r) {
        if (r && r.error) {
            return callback(r);
        }
        return callback(null, r);
    }).fail(function (jqXHR, textStatus) {
        return callback({'error': 'http_bad_response', 'data': '' + jqXHR.status, 'message': '网络好像出问题了 (HTTP ' + jqXHR.status + ')'});
    });
}

function getJSON(url, data, callback) {
    if (arguments.length===2) {
        callback = data;
        data = {};
    }
    if (typeof (data)==='object') {
        var arr = [];
        $.each(data, function (k, v) {
            arr.push(k + '=' + encodeURIComponent(v));
        });
        data = arr.join('&');
    }
    _httpJSON('GET', url, data, callback);
}

function postJSON(url, data, callback) {
    if (arguments.length===2) {
        callback = data;
        data = {};
    }
    _httpJSON('POST', url, data, callback);
}

function _display_error($obj, err) {
    if ($obj.is(':visible')) {
        $obj.hide();
    }
    var msg = err.message || String(err);
    var L = ['<div class="alert alert-danger">'];
    L.push('<p>Error: ');
    L.push(msg);
    L.push('</p><p>Code: ');
    L.push(err.error || '500');
    L.push('</p></div>');
    $obj.html(L.join(''));
}

function error(err) {
    _display_error($('#error'), err);
}

function fatal(err) {
    _display_error($('#loading'), err);
}

