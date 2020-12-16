"use strict"


function getHomeProducts() {
    $.ajax({
        url: "/onlineshopping/retrieveHomeProducts",
        dataType: "json",
        success: updateHomePage,
    });
}

/* 
item_cnt: the i th product that I am appending to view
num_item_per_row: number of products that will be fit in a row
end: true if this product is the end of the list
name: product name
description: product description
price: product price
quant: available quantity
id: product id
*/
function buildHTMLString(item_cnt, num_item_per_row, end, name, description, price, quant, id, has_photo) {
    let image_source;
    if (has_photo) { // use the photo in database
        image_source = '"/onlineshopping/photo/' + id + '"';
    }else {
        image_source = '"/static/onlineshopping/no-image-found.png"';
    }
    let result = '';
    if (item_cnt == 0) {
        result += '<div class="carousel-item active">' +
                    '<div class="row">';
    }else if(item_cnt % num_item_per_row == 0) {
        result += '<div class="carousel-item">' +
                    '<div class="row">';
    }
    result += '<div class="col-md-4">' + 
                   '<div class="card mb-2">' + 
                        '<img class="card-img-top" src=' + image_source + 'alt="Card image cap" style="border-radius: 25px; width: 348px;height: 348px">' +
                        '<div class="card-body">' +
                            '<h4 class="card-title"> ' + name + ' </h4>' +
                            '<p class="card-text">Description: ' + description + '</p>' +
                            '<p class="card-text">Price: ' + price + '</p>' +
                            '<p class="card-text">Available Quantity: ' + quant + '</p>' +
                            '<form action="/onlineshopping/add_product/'+ id +'" method = "post">' +
                                '<div class="form-group row">' +
                                    '<label for="quantity-input" class="col-sm-5 col-form-label">Quantity:</label>' +
                                    '<div class="col-sm-5">' +
                                        '<input type="number" class="form-control" id = "quantity-input" name="product_quantity" min="1" max="{{'+ quant +'}}" required>' +
                                    '</div>' +
                                '</div>' +
                                '<div class="form-group row">' +
                                    '&nbsp; &nbsp;' +
                                    '<button type="submit" class="btn btn-outline-primary" name="cart">ADD TO CART</button>' +
                                    '&nbsp; &nbsp;' +
                                    '<button type="submit" class="btn btn-outline-success" name="buy" onclick="BuyCartItems()">BUY</button>' +
                                '</div>' +
                                '<input type="hidden" name="csrfmiddlewaretoken" value="'+ getCSRFToken() +'">' +
                            '</form>' +
                        '</div>' +
                    '</div>' +
              '</div>';
    // for carousel-item and row class
    if ((item_cnt % num_item_per_row == 2) || end) {
        result += '</div>' +
                 '</div>';   
    }
    return result;
}

function updateHomePage(response) {
    if (Array.isArray(response)) {
        // do work to update
        let element_id = "#best-selling-items";
        let item_cnt = 0;
        let num_item_per_row = 3;
        let total_item = response.length;
        let htmlText = '';
        $(response).each(function() {
            htmlText += buildHTMLString(item_cnt, num_item_per_row, item_cnt == (total_item - 1), 
                                        this.name, this.description, this.price, this.quant, parseInt(this.id), this.has_photo);
            item_cnt += 1;
        });
        $(element_id).append(htmlText);
    }
}

function DeleteCartItems() {
    var ids = []
    var elements = document.querySelectorAll("[class=item_checkbox]");
    for (var i= 0; i < elements.length; i++) {
        if (elements[i].checked){
			let str = elements[i].id
            let id = parseInt(str.substring(14))
            ids.push(id)
        }
    }
    $.ajax({
        url: "/onlineshopping/shoppingCart",
        type: "POST",
        data: "action="+"delete"+"&ids="+ids+"&csrfmiddlewaretoken="+getCSRFToken(),
        dataType : "json",
        //success: deleteChecked,
        success: function(result) { 
            document.location.href = '/onlineshopping/shoppingCart';
        },
        error: updateError
    });
}

function BuyCartItems() {
    var ids = []
	var elements = document.querySelectorAll("[class=item_checkbox]");
    for (var i= 0; i < elements.length; i++) {
        if (elements[i].checked){
			let str = elements[i].id
			let id = parseInt(str.substring(14))
            ids.push(id)
        }
	}
	
    $.ajax({
        url: "/onlineshopping/shoppingCart",
        type: "POST",
        data: "action="+"buy"+"&ids="+ids+"&csrfmiddlewaretoken="+getCSRFToken(),
        dataType : "json",
        success: function(result) { 
            document.location.href = '/onlineshopping/payment';
        },
        error: updateError
    });
}

function deleteChecked(ids) { 
    for (var i= 0; i < ids.length; i++) {
        let div_id = "item_" + ids[i]
        let elem = document.getElementById(div_id);
        elem.parentNode.removeChild(elem);
	}
}

function minusQuantity(cartItem_id) {
    var input = document.getElementById("quantity_"+cartItem_id);
    if (parseInt(input.value)>1) {
        $.ajax({
            url: "/onlineshopping/minusQuantity",
            type: "POST",
            data: "id="+cartItem_id+"&csrfmiddlewaretoken="+getCSRFToken(),
            dataType : "json",
            success: function(dic) {
                if (parseInt(input.value)-1 == dic['quantity']) input.value = dic['quantity'];
                else displayError("Please use delete button.")
            },
            error: updateError
        });
    }
}

function plusQuantity(cartItem_id) {
    $.ajax({
        url: "/onlineshopping/plusQuantity",
        type: "POST",
        data: "id="+cartItem_id+"&csrfmiddlewaretoken="+getCSRFToken(),
        dataType : "json",
        success: function(dic) { 
            let input = document.getElementById("quantity_"+cartItem_id);
            input.value = dic['quantity'];
        },
        error: updateError
    });
}

function updateError(xhr, status, error) {
    displayError('Status=' + xhr.status + ' (' + error + ')')
}

function displayError(message) {
    var span = document.getElementById('error');
    
    while( span.firstChild ) {
        span.removeChild( span.firstChild );
    }
    span.appendChild( document.createTextNode(message) );
}

function getCSRFToken() {
    let cookies = document.cookie.split(";")
    for (let i = 0; i < cookies.length; i++) {
        let c = cookies[i].trim()
        if (c.startsWith("csrftoken=")) {
            return c.substring("csrftoken=".length, c.length)
        }
    }
    return "unknown";
}


// if reduce quantity to 0, delete
// if exceed quantity, show message


