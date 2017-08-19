library(RWeka)
library(partykit)
library(data.tree)

# TODO:
# - don't forget to work only on data.pred[data.pred$class==TRUE,]
# - warning: dependance between variables: for example, adding a new tag, increases html_length
# - variables: aggregate? for example, sumup all html_event_* on a new html_event var
# - add K-fold

predicted_class_leaves <- function(partytree) {
    # DEPRECATED
    # compute the predicted class for each terminal nodes
    # usage: pred_terminal_nodes['49]
    terminal_table <- as.matrix(do.call("table", fitted(partytree)))
    pred_terminal_nodes <- colnames(terminal_table)[apply(terminal_table,1,which.max)]
    names(pred_terminal_nodes) <- rownames(test)
    return(pred_terminal_nodes)
}

extract_slit_conditon <- function(node_name, partytree, data.tree) {
    # extract the condition associated with the split of the node
    # inputs:
    #   - node_name: the name of the node
    #   - partytree: the full decision tree as party class
    #   - data.tree: the same tree as data.tree class
    # output:
    #   - a character string of format: "variable >= 0"
    parent_name <- FindNode(data.tree, node_name)$parent$name # the parent node name extracted from the data.tree tree 
    if (is.null(parent_name)) 
        stop('error extracting condition. you are probably requesting the condition of the root node or an node_name that doesn\'t exist')
    condition_node_full <- partykit:::.list.rules.party(partytree, i = node_name)
    condition_parent_full <- partykit:::.list.rules.party(partytree, i = parent_name)
    if (condition_parent_full == "") { # node is the children of the root
        condition_node <- condition_node_full
    } else {
        condition_node <- sub(condition_parent_full, '', condition_node_full, fixed = TRUE)
        # this is "hand-made": we removed the parent condition from the condition of the node
        # ex: remove "variable1 >= 1 & variable2 < 42" from "variable1 >= 1 & variable2 < 42 & variable 3 > 0"
        # may fail if the condition_node is not at the end or at the begining. But seems to be always at the end.
        # We check the validity below
    }
    condition_node <- sub('^[[:space:]]*&[[:space:]]*', '', condition_node) # remove the extra &
    if (grepl('&', condition_node, fixed = T)) { # sub extration failed, and we have more than 1 condition
        stop('error extracting condition')
    }
    return(condition_node)
}

extract_variable_name <- function(condition, var_names = NULL) {
    # return the variable name of condition
    # condition format: "variable >= 0"
    # additional check that var_name is in var_names
    var_name <- regmatches(condition, regexpr('([a-zA-Z0-9_\\-\\.]+)', condition))
    if (! is.null(var_names)) {
        if (! var_name %in% var_names)
            stop('error extracting variable name')
    }
    return(var_name)
}

extract_break <- function(condition) {
    # return the break point of condition as integer or numeric
    # condition format: "variable >= 0"
    break_chr <- regmatches(condition, regexpr('([0-9.]+)$', condition))
    if (length(break_chr) == 0) {
        # no match
        stop('condition break not supported')
    }
    if (grepl('.', break_chr, fixed = T)) {
        # numeric
        return(as.numeric(break_chr))
    } else {
        # integer
        return(as.integer(break_chr))
    }
}

condition_satisfies_constraints <- function(condition, constraints, var_names) {
    # goal: know if data_adv con be modified to satisfy condition and respect constraints
    # inputs:
    #   - condition: format should be "variable >= 0"
    #   - constraints: list of one logical for each variable
    #   - var_names: vector of possible variables names (additional check)
    # output:
    #   - TRUE, if applying a perturbation to satisfy condition doesn't violate a positive 
    # constraint on the condition variable indicated by constraints
    #   - FALSE, in other cases
    # note: we don't need data, because when the function will be called, data will never 
    # satisfies condition (data_adv is associated to a node and condition corresponds to 
    # one of its siblings)
    var_name <- extract_variable_name(condition, var_names)
    if (! constraints[[var_name]]) { # if no constraint on the variable of the condition
        return(TRUE)
    } else { # if constraint on the current split variable
        # keep in mind that data_adv will never satisfy condition
        if (grepl('<', condition, fixed=T)){ # condition is < or <=
            # constraint is not fullfield, ie. current value of var_name of data_adv is > break_condition
            # perturbation needed to satisfy condition is negative
            # Not possible
            return(FALSE)
        } else if (grepl('>', condition, fixed=T)) { # condition is > or >=
            # perturbation is positive
            # Possible
            return(TRUE)
        } else {
            stop('error parsing condition, operator not supported')
        }
    }
}

data_satisfies_condition <- function(data, condition) {
    # inputs:
    #   - data:-row data.frame
    #   - condition: format "variable > 0"
    # output:
    #   - TRUE if data do satisfy condition
    #   - FALSE else
    var_name <- extract_variable_name(condition)
    assign(var_name, data[,var_name])
    condition_bool <- eval(parse(text=condition)) # scared?
    return(condition_bool)
}

apply_pertubation <- function(data, condition) {
    # return a modified data that satisfy condition
    var_name <- extract_variable_name(condition, var_names = colnames(data))
    break_condition <- extract_break(condition)
    if (grepl('<=|>=', condition)){ # condition is <= or >=
        # set var_name to the break point
        data[, var_name] <- break_condition
    } else if (grepl('<', condition, fixed=T)) {
        if (is.integer(data[, var_name])) {
            data[, var_name] <- as.integer(break_condition) - 1L
        } else { 
            stop('var type not supported')
        }
    } else if (grepl('>', condition, fixed=T)) {
        if (is.integer(data[, var_name])) {
            data[, var_name] <- as.integer(break_condition) + 1L
        } else {
            stop('var type not supported')
        }
    } else {
        stop('error parsing condition, operator not supported')
    }
    return(data)
}


find_adversarial_example <- function(partytree, data.tree, newdata, legitimate_class = "TRUE", constraints) {
    # TODO
    # inputs:
    #   - partytree: decision tree in party class
    #   - data.tree: decision tree in data.tree class (for efficiency)
    #   - newdata: 1-row data.frame representing the observation to perturbate
    #   - legitimate_class: the legitimate class of newdata (always TRUE in our case: we want a malicious page to appear benign)
    #   - constraints: list of logical, named as the variable names. Each logical indicates if the perturbations 
    #     applied to the corresponded variable should be positive
    # output:
    # TODO
    x_adv <- newdata
    legitimate_leaf <- predict(partytree, newdata, type = "node")
    current_node <- legitimate_leaf
    visited_nodes <- vector()
    path_history <- vector(mode = 'list')
    var_names <- colnames(newdata)
    
    while(predict(partytree, x_adv) == legitimate_class) {
        # if we arrive at the root of the tree, the search is unsuccessful
        if (current_node == data.tree$name) { # name of the root node
            return(NULL)
        }
        visited_nodes <- c(visited_nodes, current_node) # we have visited the current node and we will visit another one
        
        siblings <- FindNode(data.tree, current_node)$siblings # list of the siblings of current_node
        siblings_names <- sapply(siblings, FUN = function(x) return(x$name))
        
        if (any(! siblings_names %in% visited_nodes)) { # if not all siblings of current node were visited
            # change current_node to a new sibling
            current_node <- siblings_names[! siblings_names %in% visited_nodes][1] # first sibling node that were not visited
            condition_node <- extract_slit_conditon(current_node, partytree, data.tree)
            if (data_satisfies_condition(x_adv, condition_node)) {
                # x_adv should never satisfy the condition (because we just moved to a new branch)
                stop('condition is satisfied. think about your algorithm again!')
            }
            if(condition_satisfies_constraints(condition_node, constraints, var_names)) { # the constraint is satisfied or there is no constraint
                x_adv <- apply_pertubation(x_adv, condition_node) # apply perturbation to satisfy condition_node
                current_node <- predict(partytree, x_adv, type = "node") # move to the new leaf
            }
        } else { # we have visited all the siblings of the current node
            current_node <- siblings[[1]]$parent$name # move to the parent of the siblings (using data.tree)
        }
    }
    return(x_adv)
}


# Test runs

data <- read.csv('data.csv')
# convert factor to logical when appropriate
for (var in colnames(data)) {
    if (is.factor(data[,var])) {
        if (all(levels(data[,var]) %in% c("False", "True"))) {
            #data[,var] = as.logical(data[,var])
            data[,var] = as.integer(as.logical(data[,var])) # until the fix for the bug in logical variable handling in partykit, converts to int
        }
    }
}

data$class <- as.factor(as.logical(data$class))
str(data)

set.seed(42)
n.train <- floor(nrow(data)*0.8)
is.train <- sample(c(rep(TRUE, n.train), rep(FALSE, nrow(data) - n.train)))
data.train <- data[is.train,]
data.pred <- data[!is.train,]

# options for J48
WOW(J48)
# -N <number of folds>
# ...

m1 <- J48(class~., data = data.train)
m1
summary(m1)
table(data.pred$class, predict(m1, data.pred))
prop.table(table(data.pred$class, predict(m1, data.pred)))*100
sum(diag(prop.table(table(data.pred$class, predict(m1, data.pred)))))
if(require("party", quietly = TRUE)) plot(m1)
plot(m1, type="simple")


prty <- as.party(m1)
tree <- as.Node(prty)
partytree <- prty
data.tree <- tree
newdata <- data[1,]


constraints <- vector(mode='list', length=ncol(data))
names(constraints) <- colnames(data)
# TRUE: contraint to an increase. derivative should be >=0
# to apply a negaive constraint, just transform your variable to the opposite
# becareful, logical variable are converted to integer
constraints[['url_special_characters']] = TRUE # 0->1 ok ; 1->0 no
# constraint all variables, except: js_file (? -> pas à contraindre, on suppose que l'algo est le seul web firewall), url_* (?)
for (i in colnames(data)) {
    constraints[[i]] = TRUE
}
# TODO: variables:
# - url_number_keywords
# - js_method_alert

# TODO: impact of perturbations on:
# - url_length
# - html_length

find_adversarial_example(partytree, data.tree, newdata, constraints = constraints)

# TODO: use data.pred or data.train or both?
data.pred.malicious <- data.pred[data.pred$class==TRUE,] 

run_adversarial_strategy <- function(constraints) {
    # TODO: cleaner
    successful_bypasses <- data.frame()
    for (i in 1:nrow(data.pred.malicious)) {
        cat('*')
        newdata_adv <- find_adversarial_example(partytree, data.tree, newdata = data.pred.malicious[i, ], constraints = constraints)
        if (! is.null(newdata_adv))
            successful_bypasses <- rbind(successful_bypasses, newdata_adv)
    }
    # number of bypasses
    cat('\nnumber of bypasses: ', nrow(successful_bypasses), '\n')
    # % of escape
    cat('number of bypasses: ', nrow(successful_bypasses)/nrow(data.pred.malicious), '\n')
}

run_adversarial_strategy(constraints)
# number of bypasses:  26 
# number of bypasses:  0.0795107 

# on train: 0.077101


# other constraints
constraints2 <- constraints
for (i in c('url_number_keywords', 'js_method_alert', 'js_min_define_function')) {  
    # url_number_domain ?
    # url_cookie ?
    # js_min_function_calls ?
    constraints2[[i]] <- FALSE
}

run_adversarial_strategy(constraints2)
# number of bypasses:  27 
# number of bypasses:  0.08256881 

# on train: 0.07941403
