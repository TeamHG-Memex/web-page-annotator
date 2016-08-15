$(document).ready(function () {
    console.log('hi from parent');

    var $childPage = $('iframe#child-page');
    var $window = $(window);

    $childPage.width($window.width());
    $childPage.height($window.height() - $childPage.offset().top);

    $(document.body).on('label-element', function (event) {
        console.log('event in parent', event);
    });
});