def includeme(config):
  # <!-- we want this view to "win" -->
  config.add_route('route', 'abc')
  config.add_view('.views.route_view', route_name='route')
  # <!-- .. even though this one has a more specific context -->
  config.add_view('.views.global_view',
                  context='pyramid.traversal.DefaultRootFactory')
  config.add_view('.views.global2_view',
                  context='pyramid.traversal.DefaultRootFactory',
                  name='global2')
  config.add_route('route2', 'def')
  # <!-- we want this view to win for route2 even though global view with 
  #     context is more specific -->
  config.add_view('.views.route2_view', route_name='route2')

  # <!-- the global view should be found for this route -->
  config.add_route('route3', 'ghi', use_global_views=True)
  # <!-- the global view should not be found for this route -->
  config.add_route('route4', 'jkl')
  # <!-- the global view should not be found for this route (/global2) -->
  config.add_route('route5', 'mno/*traverse')
  # <!-- the global view should be found for this route (/global2) -->
  config.add_route('route6', 'pqr/*traverse', use_global_views=True)
  config.add_route('route7', 'error')
  config.add_view('.views.erroneous_view', route_name='route7')
  config.add_route('route8', 'error2')
  config.add_view('.views.erroneous_view', route_name='route8')
  # <!-- we want this view to "win" for route7 as exception view -->
  config.add_view('.views.exception_view', context=RuntimeError)
  # <!-- we want this view to "win" for route8 as exception view-->
  config.add_view('.views.exception2_view', context=RuntimeError,
                  route_name='route8')
  config.add_route('route9', 'error_sub')
  config.add_view('.views.erroneous_sub_view', route_name='route9')
  # <!-- we want this view to "win" for route9 as exception view... -->
  config.add_view('.views.exception2_view', context='.views.SuperException',
                  route_name='route9')
  # <!-- ...even if we have more context-specialized view for exception -->
  config.add_view('.views.exception_view', context='.views.SubException')
