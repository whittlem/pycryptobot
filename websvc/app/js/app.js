$(document).ready(function() {
    $('#exchanges').DataTable( {
        "order": [[ 1, "asc" ]]
    } );

    $('#markets').DataTable( {
        "order": [[ 0, "asc" ]],
        'iDisplayLength': 25,
        "lengthMenu": [ [5, 10, 25, 50, 100, 250, -1], [5, 10, 25, 50, 100, 250, "All"] ]
    } );
} );