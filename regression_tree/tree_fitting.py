import numpy as np
from regression_tree import *

_DEBUG = True
_DEBUG_DETAILED = False
_DEBUG_GRAPHVIZ = True

"""
Hyperparameters

Parameters
    ----------
    _AMOUNT_RANDOM_CANDIDATE_SPLITS : #amount of random candidate splits generated for each node
    _REGRESSION_TREE_MAX_DEPTH : depth of the regression tree -> e.g. depth 5 results in 32 leaf nodes
"""
_AMOUNT_RANDOM_CANDIDATE_SPLITS = 20
_REGRESSION_TREE_MAX_DEPTH = 5

"""
Select and return best candidate split (pixel x1, pixel x2, pixel intensity threshold) for a single node.

Parameters
    ----------
    I_grayscale_image_matrix : matrix with rows of grayscale image values for extraced features/pixels
        Note: one row for each I (image) in each (I, S_hat, S_delta) triplet of our data

    residual_image_vector_matrix : matrix with rows of residual image vectors (all (194) resdiuals computed for a single image and data triplet (I, S_hat, S_delta)) 
        Note: amount and order of images / triplets (I, S_hat, S_delta) must be the same as in I_grayscale_image_matrix

    theta_candidate_splits : possible theta (pixel x1, pixel x2, pixel intensity threshold) candidate splits

    Q_I_at_node : set of indicies of images (I) for each triplet that are bucketized at current node

    mu_parent_node : mu value (avarage residual values) at parent node
        Note: parameter is None when selecting best candidate split for root node

Returns
    -------
    (pixel x1, pixel x2, pixel intensity threshold), mu_theta : best candidate split triplet and corresponding Q_theta_l, Q_thetas_r, mu_theta value needed for calculation in the next iteration
"""
def _select_best_candidate_split_for_node(I_grayscale_image_matrix, residual_image_vector_matrix, theta_candidate_splits, Q_I_at_node, mu_parent_node=None):
    sum_square_error_theta_candidate_splits = []
    mu_thetas = []
    Q_thetas_l =  []
    Q_thetas_r = []

    for theta in theta_candidate_splits:
        x1, x2, threshold = theta
        Q_theta_l = []
        Q_theta_r = []

        # bucketize images based on theta candidate split
        for index in Q_I_at_node:
            if np.abs(I_grayscale_image_matrix[index][x1] - I_grayscale_image_matrix[index][x2]) > threshold: 
                Q_theta_l.append(index)
            else:
                Q_theta_r.append(index)

        mu_theta_l = (len(Q_theta_l) and 1 / len(Q_theta_l) or 0) * np.sum(residual_image_vector_matrix[Q_theta_l], axis=0) 
        mu_theta_r = np.empty(residual_image_vector_matrix[Q_theta_r].shape)
        if mu_parent_node is None: # True if selecting candidate split for root node
            mu_theta_r = (len(Q_theta_r) and 1 / len(Q_theta_r) or 0) * np.sum(residual_image_vector_matrix[Q_theta_r], axis=0)
        else:
            mu_theta_r = (len(Q_theta_r) and 1 / len(Q_theta_r) or 0) * (len(Q_I_at_node) * mu_parent_node - len(Q_theta_l) * mu_theta_l)
    
        sum_square_error_theta = (len(Q_theta_l) * np.matmul(mu_theta_l.T, mu_theta_l)) + (len(Q_theta_r) * np.matmul(mu_theta_r.T, mu_theta_r))
        sum_square_error_theta_candidate_splits.append(sum_square_error_theta)
        mu_thetas.append((mu_theta_l , mu_theta_r))
        Q_thetas_l.append(Q_theta_l)
        Q_thetas_r.append(Q_theta_r)

    best_theta_candidate_split_index = np.argmax(sum_square_error_theta_candidate_splits)
    return theta_candidate_splits[best_theta_candidate_split_index],  Q_thetas_l[best_theta_candidate_split_index], Q_thetas_l[best_theta_candidate_split_index], mu_thetas[best_theta_candidate_split_index]

def _generate_random_candidate_splits(amount_extraced_features, amount_candidate_splits=_AMOUNT_RANDOM_CANDIDATE_SPLITS):
    random_candidate_splits = []
    for _ in range(0, amount_candidate_splits): 
        random_x1_pixel_index = np.random.randint(0, amount_extraced_features)
        random_x2_pixel_index = np.random.randint(0, amount_extraced_features)
        while (random_x1_pixel_index == random_x2_pixel_index):
            random_x2_pixel_index = np.random.randint(0, amount_extraced_features)

        random_threshold = np.random.randint(0, 256) # we take the absolute value for the pixel intensity differnece (0-255)
        random_candidate_splits.append((random_x1_pixel_index, random_x2_pixel_index, random_threshold))
    return random_candidate_splits

def _generate_root_node(regression_tree, I_grayscale_image_matrix, residual_image_vector_matrix, Q_I_at_root):
    random_candidate_splits_root = _generate_random_candidate_splits(I_grayscale_image_matrix.shape[0])
    (best_x1_pixel_index_root, best_x2_pixel_index_root, best_threshold_root), Q_theta_l_root, Q_theta_r_root, mu_theta_root = _select_best_candidate_split_for_node(
        I_grayscale_image_matrix,
        residual_image_vector_matrix,
        random_candidate_splits_root,
        Q_I_at_root
    )
    return regression_tree.create_node(best_x1_pixel_index_root, best_x2_pixel_index_root, best_threshold_root), Q_theta_l_root, Q_theta_r_root, mu_theta_root 

def _generate_leaf_node(regression_tree, avarage_residual_image_vector, parent_id):
    return regression_tree.create_leaf(avarage_residual_image_vector, parent_id)

def _generate_child_nodes(
        regression_tree,
        current_node_id, 
        current_depth, 
        max_depth, 
        I_grayscale_image_matrix, 
        residual_image_vector_matrix, 
        Q_theta_l,
        Q_theta_r,
        mu_parent_node
    ):
    if current_depth == max_depth-1:
        mu_theta_l, mu_theta_r = mu_parent_node
        left_leaf_node = _generate_leaf_node(regression_tree, mu_theta_l, parent_id=current_node_id)
        right_leaf_node = _generate_leaf_node(regression_tree, mu_theta_r, parent_id=current_node_id)
        return True

    random_candidate_splits_left_child = _generate_random_candidate_splits(I_grayscale_image_matrix.shape[0])
    (best_x1_pixel_index_left_child, best_x2_pixel_index_left_child, best_threshold_left_child), Q_theta_l_left_child, Q_theta_r_left_child, mu_theta_left_child = _select_best_candidate_split_for_node(
        I_grayscale_image_matrix,
        residual_image_vector_matrix,
        random_candidate_splits_left_child,
        Q_theta_l,
        np.sum(mu_parent_node, axis=0)
    )

    random_candidate_splits_right_child = _generate_random_candidate_splits(I_grayscale_image_matrix.shape[0])
    (best_x1_pixel_index_right_child, best_x2_pixel_index_right_child, best_threshold_right_child), Q_theta_l_right_child, Q_theta_r_right_child, mu_theta_right_child = _select_best_candidate_split_for_node(
        I_grayscale_image_matrix,
        residual_image_vector_matrix,
        random_candidate_splits_right_child,
        Q_theta_r,
        np.sum(mu_parent_node, axis=0)
    )

    # we are always creating two new nodes at a time
    left_node = regression_tree.create_node(best_x1_pixel_index_left_child, best_x2_pixel_index_left_child, best_threshold_left_child, parent_id=current_node_id)  # left node, has parent current_node
    right_node = regression_tree.create_node(best_x1_pixel_index_right_child, best_x2_pixel_index_right_child, best_threshold_right_child, parent_id=current_node_id)  # right node, has parent current_node

    return (
        _generate_child_nodes(
            regression_tree,
            left_node.id, 
            current_depth+1, 
            max_depth, 
            I_grayscale_image_matrix,
            residual_image_vector_matrix,
            Q_theta_l_left_child,
            Q_theta_r_left_child,
            mu_theta_left_child
        ), _generate_child_nodes(
            regression_tree,
            right_node.id, 
            current_depth+1, 
            max_depth, 
            I_grayscale_image_matrix,
            residual_image_vector_matrix,
            Q_theta_l_right_child,
            Q_theta_r_right_child,
            mu_theta_right_child
        )
    ) 

def generate_regression_tree(I_grayscale_image_matrix, residual_image_vector_matrix):
    Q_I_at_root = [i for i in range(0, len(I_grayscale_image_matrix))]

    if _DEBUG_DETAILED:
        print("I_grayscale_image_matrix : " + str(I_grayscale_image_matrix))
        print()
        print("residual_image_vector_matrix : " + str(residual_image_vector_matrix))
        print()
        print("Q_images_at_node : " + str(Q_I_at_root))

    regression_tree = Regression_Tree()
    root_node, Q_theta_l_root, Q_theta_r_root, mu_theta_root = _generate_root_node(regression_tree, I_grayscale_image_matrix, residual_image_vector_matrix, Q_I_at_root)

    regression_tree_generation_successful = _generate_child_nodes(regression_tree, root_node.id, 0, _REGRESSION_TREE_MAX_DEPTH, I_grayscale_image_matrix, residual_image_vector_matrix, Q_theta_l_root, Q_theta_r_root, mu_theta_root)
    print("🌳 regression tree successfully generated ... ", regression_tree_generation_successful)

    return regression_tree

# TODO restirct depth by setting minimum amount of images bucketized in one node/leaf
# TODO build function to search trough the regression tree in order to find correct landmark delta values for each Image

I_grayscale_image_matrix = np.random.randint(0, 256, (20*5, 400)) # shape (N=n*R, #extraced pixels)
residual_image_vector_matrix = np.random.rand(20*5, 194) # only positive values for test example ; shape (N=n*R, 194)

regression_tree = generate_regression_tree(I_grayscale_image_matrix, residual_image_vector_matrix)

if _DEBUG:
    print()
    print(regression_tree.get_tree_description(detailed=_DEBUG_DETAILED))
    if _DEBUG_GRAPHVIZ:
        graphviz = regression_tree.get_dot_graphviz_source()
        graphviz_file = open('./regression_tree/graphviz_output.txt', 'w', encoding='utf-8')
        graphviz_file.write(graphviz)
        graphviz_file.close()
