(function () {
    if (typeof jQuery === 'undefined') {
        console.warn('bundle.js requires jQuery');
        return;
    }
    $(function () {
        if (location.hash.substr(0, 2) == '#!') {
            $("a[href='#" + location.hash.substr(2) + "']").tab('show');
        }
        $('[data-toggle="tooltip"]').tooltip();
        $("a[data-toggle='tab']").on('shown.bs.tab', function (e) {
            var hash = $(e.target).attr('href');
            if (hash.substr(0, 1) == '#') {
                location.replace('#!' + hash.substr(1));
            }
        });
        $('input.date').datepicker({
            showOtherMonths: true,
            selectOtherMonths: true,
            changeMonth: true,
            changeYear: true,
            dateFormat: 'yy-mm-dd',
        });
    });
    window.enableButtonForCheckboxes = function (btn_selector, checkbox_class) {
        var checkbox_selector = 'input[type=checkbox].' + checkbox_class;
        $(checkbox_selector).change(function () {
            $(btn_selector).prop('disabled', $(checkbox_selector + ':checked').length == 0);
        });
    };
})();
