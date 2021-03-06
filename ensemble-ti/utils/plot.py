import math
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import phate
import umap
 
from matplotlib import cm
from sklearn.manifold import TSNE

from models.ti.graph import compute_connectivity_graph, compute_trajectory_graph


def plot_embeddings(X, figsize=None, **kwargs):
    assert X.shape[-1] == 2
    plt.figure(figsize=figsize)
    plt.scatter(X[:, 0], X[:, 1], **kwargs)
    plt.gca().set_axis_off()
    plt.show()


def generate_plot_embeddings(X, method='tsne', **kwargs):
    if method == 'phate':
        phate_op = phate.PHATE(**kwargs)
        X_phate = phate_op.fit_transform(X)
        return X_phate
    elif method == 'tsne':
        tsne = TSNE(n_components=2, **kwargs)
        X_tsne = tsne.fit_transform(X)
        return X_tsne
    elif method == 'umap':
        u = umap.UMAP()
        X_umap = u.fit_transform(X)
    else:
        raise ValueError(f'Unsupported embedding method type: {method}')


def plot_gene_expression(adata, genes, nrows=1, cmap=None, figsize=None, marker_size=5, obsm_key='X_embedded'):
    # BUG: Currently displays the colormap for
    # each gene individually. Update to get a common vmin and
    # vmax for all the genes that need to be plotted
    assert type(genes).__name__ in ['list', 'tuple']
    try:
        X_embedded = adata.obsm[obsm_key]
    except KeyError:
        raise Exception(f'Key {obsm_key} not found in {adata}')

    try:
        X_imputed = adata.obsm['X_magic']
    except KeyError:
        print('MAGIC imputed data not found. Using raw counts instead')
        X_imputed = adata.X
    
    assert X_embedded.shape[-1] == 2
    cmap = cm.Spectral_r if cmap is None else cmap
    raw_data_df = adata.to_df()
    imputed_data_df = pd.DataFrame(X_imputed, columns=raw_data_df.columns, index=raw_data_df.index)

    # Remove genes excluded from the analysis
    excluded_genes = set(genes) - set(raw_data_df.columns)
    if len(excluded_genes) != 0:
        print(f'The following genes were not plotted: {excluded_genes}')

    net_genes = list(set(genes) - set(excluded_genes))
    ncols = math.ceil(len(net_genes) / nrows)
    gs = plt.GridSpec(nrows=nrows, ncols=ncols)
    fig = plt.figure(figsize=figsize)
    gene_index = 0
    for row_idx in range(nrows):
        for col_idx in range(ncols):
            gene_name = net_genes[gene_index]
            gene_expression = imputed_data_df[gene_name].to_numpy()
            axes = plt.subplot(gs[row_idx, col_idx]) 
            axes.scatter(
                X_embedded[:, 0], X_embedded[:, 1], s=marker_size,
                c=gene_expression, cmap=cmap
            )
            axes.set_title(gene_name)
            axes.set_axis_off()
            gene_index = gene_index + 1

            # Display the Colorbar
            vmin = np.min(gene_expression)
            vmax = np.max(gene_expression)
            normalize = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
            cax, _ = matplotlib.colorbar.make_axes(axes)
            matplotlib.colorbar.ColorbarBase(cax, norm=normalize, cmap=plt.get_cmap(cmap))
    plt.show()


def plot_clusters(adata, cluster_key='communities', embedding_key='X_embedding', cmap=None, figsize=(12, 8)):
    communities = adata.obs[cluster_key]
    embeddings = adata.obsm[embedding_key]
    # Only 2d embeddings can be visualized :)
    assert embeddings.shape[-1] == 2

    plt.figure(figsize=figsize)
    axes = plt.subplot(111)
    scatter = axes.scatter(embeddings[:, 0], embeddings[:, 1], c=communities, s=8, cmap=cmap)
    legend1 = axes.legend(*scatter.legend_elements(num=len(np.unique(communities))), loc="center left", title="Cluster Id", bbox_to_anchor=(1, 0.5))
    axes.add_artist(legend1)
    axes.set_axis_off()
    plt.show()


def plot_pseudotime(adata, embedding_key='X_embedded', pseudotime_key='X_pseudotime',cmap=None, figsize=None, marker_size=5, **kwargs):
    pseudotime = adata.obs[pseudotime_key]
    X_embedded = adata.obsm[embedding_key]

    # Plot
    plt.figure(figsize=figsize)
    plt.scatter(
        X_embedded[:, 0], X_embedded[:, 1], s=marker_size,
        c=pseudotime, cmap=cmap, **kwargs
    )
    plt.gca().set_axis_off()

    # Display the Colorbar
    vmin = np.min(pseudotime)
    vmax = np.max(pseudotime)
    normalize = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    cax, _ = matplotlib.colorbar.make_axes(plt.gca())
    matplotlib.colorbar.ColorbarBase(cax, norm=normalize, cmap=plt.get_cmap(cmap))
    plt.show()


def plot_trajectory_graph(embeddings, communities, cluster_connectivities, start_cell_ids, cmap='YlGn', figsize=(16, 12), node_size=400, font_color='black'):
    g, node_positions = compute_trajectory_graph(embeddings, communities, cluster_connectivities, start_cell_ids)
    # Draw the graph
    plt.figure(figsize=figsize)
    plt.axis('off')
    edge_weights = [0.2 + w for _, _, w in g.edges.data("weight")]
    nx.draw_networkx(g, pos=node_positions, cmap=cmap, node_color=np.unique(communities), font_color=font_color, node_size=node_size, width=edge_weights)


def plot_connectivity_graph(embeddings, communities, cluster_connectivities, mode='undirected', cmap='YlGn', figsize=(16, 12), node_size=400, font_color='black'):
    g, node_positions = compute_connectivity_graph(embeddings, communities, cluster_connectivities, mode=mode)
    # Draw the graph
    plt.figure(figsize=figsize)
    plt.axis('off')
    edge_weights = [0.2 + w for _, _, w in g.edges.data("weight")]
    nx.draw_networkx(g, pos=node_positions, cmap=cmap, node_color=np.unique(communities), font_color=font_color, node_size=node_size, width=edge_weights)


def plot_gt_milestone_network(ad, uns_mn_key='milestone_network', start_node_color='red', node_color='yellow', figsize=(12, 12), node_size=800, font_size=9):
    # NOTE: Since the dyntoy tool does not provide the spatial position
    # of the milestones, this function uses spring_layout to plot the
    # node positions. Hence the displayed graph is not guaranteed to produce
    # accurate spatial embeddings of milestones in the 2d plane.
    if uns_mn_key not in ad.uns_keys():
        raise Exception(f'Milestone network not found in uns.{uns_mn_key}')

    # Get a set of unique milestones
    mn = ad.uns[uns_mn_key]
    from_milestones = set(mn['from'].unique())
    to_milestones = set(mn['to'].unique())
    milestones = from_milestones.union(to_milestones)

    # Construct the milestone network
    milestone_network = nx.DiGraph()
    start_milestones = [ad.uns['start_milestones']] if isinstance(ad.uns['start_milestones'], str) else list(ad.uns['start_milestones'])
    color_map = []
    for milestone in milestones:
        milestone_network.add_node(milestone)
        if milestone in start_milestones:
            color_map.append(start_node_color)
        else:
            color_map.append(node_color)

    for idx, (f, t) in enumerate(zip(mn['from'], mn['to'])):
        milestone_network.add_edge(f, t, weight=mn['length'][idx])

    # Draw graph
    plt.figure(figsize=figsize)
    plt.axis('off')
    edge_weights = [1 + w for _, _, w in milestone_network.edges.data("weight")]
    nx.draw_networkx(milestone_network, pos=nx.spring_layout(milestone_network), node_size=node_size, width=edge_weights, node_color=color_map, font_size=font_size)
