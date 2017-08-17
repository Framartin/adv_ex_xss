require(partykit)
require(data.tree)

partytree <- prty
data.tree <- tree
data <- data[1,]


constrains <- vector(mode='list', length=ncol(data))
names(constrains) <- colnames(data)
# TRUE: contraint to an increase. derivative should be >=0
# to apply a negaive constraint, just transform your variable to the opposite
# becareful, logical variable are converted to integer
constrains[['url_special_characters']] = TRUE # 0->1 ok ; 1->0 no
# constraint all variables, except: js_file (? -> pas à contraindre, on suppose que l'algo est le seul web firewall), url_* (?)
for (i in colnames(data)) {
        constrains[[i]] = TRUE
}

predicted_class_leaves <- function(partytree) {
    # compute the predicted class for each terminal nodes
    # usage: pred_terminal_nodes['49]
    terminal_table <- as.matrix(do.call("table", fitted(partytree)))
    pred_terminal_nodes <- colnames(terminal_table)[apply(terminal_table,1,which.max)]
    names(pred_terminal_nodes) <- rownames(test)
    return(pred_terminal_nodes)
}

find_adversarial_node <- function(partytree, data.tree, data, constrains = NULL) {
    var_names <- colnames(data)
    adv_ex <- data
    legitimate_class <- TRUE #predict(partytree, data) # NO! We only want true-positive to be detected as false positive
    legit_leaf <- predict(partytree, data, type = "node")
    current_node <- legit_leaf
    components <- c()
    #pred_leaves <- predicted_class_leaves(partytree)
    
    while(predict(partytree, adv_ex) == legitimate_class) {
        sibling <- FindNode(data.tree, current_node)$siblings[[1]] # sibling data.tree node # TODO: J48 can have more than 2 siblings
        sibling_name <- sibling$name
        parent <- sibling$parent
        parent_name <- parent$name
        condition_sibling_full = partykit:::.list.rules.party(partytree, i = sibling_name)
        condition_parent_full = partykit:::.list.rules.party(partytree, i = parent_name)
        if (condition_parent_full == "") { # children of the root
            condition_sibling <- condition_sibling_full
        } else {
            condition_sibling = gsub(condition_parent_full, '', condition_sibling_full, fixed = TRUE)
        }
        condition_sibling = sub('[[:space:]]*&[[:space:]]*', '', condition_sibling)
        var_name <- regmatches(condition_sibling, regexpr('([a-zA-Z0-9_-.]+)', condition_sibling))
        if (! var_name %in% var_names)
            stop('error extracting variable name')
        if (! is.null(constrains[[var_name]])) { # if constraint on the current split variable
            assign(var_name, data[,var_name])
            condition_sibling_bool = eval(parse(text=condition_sibling)) # scared?
            if (! condition_sibling_bool) { # the condition is not already fullfield
                break_numeric <- as.numeric(regmatches(condition_sibling, regexpr('([0-9.]+$)', condition_sibling)))
                if (grepl('<', condition_sibling, fixed=T)){ # condition is < or <=
                    # constraint is not fullfield, ie. current value is > break_num
                    # Not possible
                    #next
                } else if (grepl('>=', condition_sibling, fixed=T)) {
                    # Possible
                    # Set variable to break_num
                    if (is.integer(adv_ex[,var_name])) {
                        adv_ex[,var_name] <- as.integer(break_numeric)
                        append(components, list(var=var_name, value=as.integer(break_numeric)))
                    } else {
                        stop('var type not supported')
                    }
                } else if (grepl('>', condition_sibling, fixed=T)) {
                    if (is.integer(adv_ex[,var_name])) {
                        adv_ex[,var_name] <- as.integer(break_numeric + 1)
                        append(components, list(var=var_name, value=as.integer(break_numeric)))
                    } else {
                        stop('var type not supported')
                    }
                } else {
                    stop('error parsing condition, operator not supported')
                }
                
            }
        }
        append(components, 1)
    }
    return(legit_leaf)
}

find_adversarial_node(partytree = b, data.tree=tree , data = data.train[1,])


exhaustive_search <- function(partytree, data.tree, data, constrains = NULL) {
    legitimate_class <- predict(partytree, data)
    legit_leaf <- predict(partytree, data, type = "node")
    leaves <- nodeids(partytree, terminal = TRUE)
    
}

# don't forget to work only on data.pred[data.pred$class==TRUE,]
# warning: dependance between variables: for example, adding a new tag, increases html_length

extract_variable_name <- function(condition, var_names) {
    # return the variable name of condition
    # condition format: "variable >= 0"
    # additional check that var_name is in var_names
    var_name <- regmatches(condition, regexpr('([a-zA-Z0-9_\\-\\.]+)', condition))
    if (! var_name %in% var_names)
        stop('error extracting variable name')
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

satisfies <- function(condition, constrains, var_names) {
    # goal: know if data_adv con be modified to satisfy condition and respect constrains
    # inputs:
    #   - condition: format should be "variable >= 0"
    #   - constrains: list of one logical for each variable
    #   - var_names: vector of possible variables names (additional check)
    # output:
    #   - TRUE, if applying a perturbation to satisfy condition doesn't violate a positive 
    # constraint on the condition variable indicated by constrains
    #   - FALSE, in other cases
    # note: we don't need data, because when the function will be called, data will never 
    # satisfies condition (data_adv is associated to a node and condition corresponds to 
    # one of its siblings)
    var_name <- extract_variable_name(condition, var_names)
    if (! constrains[[var_name]]) { # if no constraint on the variable of the condition
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

apply_pertubation <- function(data, condition) {
    # return a modified data that satisfy condition
    var_name <- extract_variable_name(condition, var_names = colnames(data))
    break_condition <- extract_break(condition)
    if (grepl('<=|>=', condition)){ # condition is <= or >=
        # set var_name to the break point
        data[, var_name] <- break_condition
    } else if (grepl('<', condition, fixed=T)) {
        if (is.integer(adv_ex[, var_name])) {
            data[, var_name] <- as.integer(break_condition) - 1
        } else { 
            stop('var type not supported')
        }
    } else if (grepl('>', condition, fixed=T)) {
        if (is.integer(adv_ex[, var_name])) {
            data[, var_name] <- as.integer(break_condition) + 1
        } else {
            stop('var type not supported')
        }
    } else {
        stop('error parsing condition, operator not supported')
    }
    return(data)
}
