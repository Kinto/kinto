def includeme(config):
    config.add_route('gameactions_pet_get_pets', '/pet',
                     request_method='GET')
    config.add_route('gameactions_pet_care_for_pet', '/pet',
                     request_method='POST')
    config.add_view('.views.PetRESTView',
                    route_name='gameactions_pet_get_pets',
                    attr='GET',
                    permission='view',
                    renderer='json')
    config.add_view('.views.PetRESTView',
                    route_name='gameactions_pet_care_for_pet',
                    attr='POST',
                    permission='view',
                    renderer='json')
