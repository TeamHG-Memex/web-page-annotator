$(document).ready(function () {

    function adjustIFrame() {
        var $childPage = $('iframe#child-page');
        var $window = $(window);

        $childPage.width($window.width());
        $childPage.height($window.height() - $childPage.offset().top);
    }

    adjustIFrame();

    $(window).on('resize', adjustIFrame);

    $(document.body).on('label-element', function (event) {
        console.log('event in parent', event);
    });

});