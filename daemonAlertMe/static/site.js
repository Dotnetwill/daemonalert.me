$(function() {
    //Notifications
    $('.notification-success').fadeIn('slow');
    $('.notification-error').fadeIn('slow');

    $('.notification-error').click(function(){
        $(this).fadeOut();
    });

    $('.notification-success').click(function(){
        $(this).fadeOut();
    });
});

    $(function (){
        $('a.add-alert').click(function() {
            var container = $(this).parents('.ignore-result');
            var target = container.find('.url_watched').attr('href');
            $('#add_alert_url').attr('href', target);
            $('#add_alert_url').html(target);
            $('#hidden_url').attr('value', target);
        });
        $("a[rel*=leanModal]").leanModal({closeButton: '#close-button'}); 
    });

